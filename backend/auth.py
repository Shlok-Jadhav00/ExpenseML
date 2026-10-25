"""Cookie-session authentication and CSRF protection for the pilot website."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
from datetime import datetime, timedelta
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserSession

SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", "604800"))
SESSION_IDLE_TIMEOUT_SECONDS = int(os.getenv("SESSION_IDLE_TIMEOUT_SECONDS", "86400"))
IS_PRODUCTION = os.getenv("APP_ENV", "development").lower() == "production"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true" if IS_PRODUCTION else "false").lower() == "true"
SESSION_COOKIE_NAME = "__Host-expense_session" if COOKIE_SECURE else "expense_session_dev"
SESSION_SAMESITE = os.getenv("SESSION_SAMESITE", "lax")
_ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
}
_PASSWORD_HASHER = PasswordHash.recommended()
_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMIT_EVENTS: dict[tuple[str, str], list[datetime]] = {}


def utc_now() -> datetime:
    return datetime.utcnow()


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _PASSWORD_HASHER.verify(password, password_hash)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_request_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in _ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Request origin is not allowed")


def enforce_rate_limit(request: Request, action: str) -> None:
    """Apply a small per-process guard; production should also rate-limit at the proxy."""
    limit = int(os.getenv(f"{action.upper()}_RATE_LIMIT", "10"))
    window_seconds = 900
    key = (action, request.client.host if request.client else "unknown")
    now = utc_now()
    with _RATE_LIMIT_LOCK:
        events = [event for event in _RATE_LIMIT_EVENTS.get(key, []) if (now - event).total_seconds() < window_seconds]
        if len(events) >= limit:
            raise HTTPException(status_code=429, detail="Too many requests; try again later")
        events.append(now)
        _RATE_LIMIT_EVENTS[key] = events


def create_session(db: Session, user: User) -> tuple[UserSession, str]:
    now = utc_now()
    raw_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        csrf_token_hash=_hash_token(csrf_token),
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(seconds=SESSION_MAX_AGE_SECONDS),
    )
    db.add(session)
    return session, raw_token


def set_session_cookie(response, raw_token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=SESSION_SAMESITE,
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
) -> UserSession:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    session = (
        db.query(UserSession)
        .filter(UserSession.token_hash == _hash_token(raw_token), UserSession.revoked_at.is_(None))
        .first()
    )
    now = utc_now()
    if session is None or session.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if session.last_used_at and (now - session.last_used_at).total_seconds() > SESSION_IDLE_TIMEOUT_SECONDS:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    session.last_used_at = now
    db.commit()
    return session


def get_current_user(session: UserSession = Depends(get_current_session)) -> User:
    user = session.user
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def require_csrf(
    request: Request,
    session: UserSession = Depends(get_current_session),
) -> None:
    validate_request_origin(request)
    provided = request.headers.get("X-CSRF-Token")
    if not provided or not hmac.compare_digest(_hash_token(provided), session.csrf_token_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def session_csrf_token(session: UserSession, db: Session) -> str:
    token = secrets.token_urlsafe(32)
    session.csrf_token_hash = _hash_token(token)
    db.commit()
    return token


def same_site_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    parsed = urlparse(origin)
    return bool(parsed.scheme and parsed.netloc and origin in _ALLOWED_ORIGINS)
