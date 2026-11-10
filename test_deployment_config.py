import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth import get_current_user, require_csrf
from backend.database import Base, get_db
from backend.main import app
from backend.models import User
from ml.anomaly_model import category_stats, model


@pytest.fixture
def deployment_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, session_factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def registration_payload(email, *, research_consent=False):
    return {
        "email": email,
        "password": "beta-password-123",
        "privacy_notice_version": "2026-11-beta-1",
        "privacy_notice_accepted": True,
        "research_consent": research_consent,
        "research_consent_version": "2026-11-beta-1" if research_consent else None,
    }


def test_beta_allowlist_accepts_invited_and_rejects_uninvited(deployment_client, monkeypatch):
    client, _ = deployment_client
    monkeypatch.setenv("BETA_MODE", "true")
    monkeypatch.setenv("BETA_ALLOWED_EMAILS", "invited@example.com")

    allowed = client.post("/auth/register", json=registration_payload("invited@example.com"))
    rejected = client.post("/auth/register", json=registration_payload("other@example.com"))

    assert allowed.status_code == 201
    assert rejected.status_code == 403


def test_beta_empty_allowlist_denies_registration(deployment_client, monkeypatch):
    client, _ = deployment_client
    monkeypatch.setenv("BETA_MODE", "true")
    monkeypatch.setenv("BETA_ALLOWED_EMAILS", "")

    response = client.post("/auth/register", json=registration_payload("nobody@example.com"))

    assert response.status_code == 403


def test_privacy_notice_is_mandatory_but_research_is_optional(deployment_client, monkeypatch):
    client, _ = deployment_client
    monkeypatch.setenv("BETA_MODE", "false")

    missing_notice = client.post(
        "/auth/register",
        json={
            "email": "missing@example.com",
            "password": "beta-password-123",
            "privacy_notice_version": "2026-11-beta-1",
            "privacy_notice_accepted": False,
            "research_consent": False,
        },
    )
    accepted_without_research = client.post(
        "/auth/register",
        json=registration_payload("ordinary@example.com"),
    )

    assert missing_notice.status_code == 422
    assert accepted_without_research.status_code == 201
    assert accepted_without_research.json()["user"]["research_consent"] is False


def test_research_consent_withdrawal_is_immediate(deployment_client, monkeypatch):
    client, session_factory = deployment_client
    monkeypatch.setenv("BETA_MODE", "false")
    response = client.post(
        "/auth/register",
        json=registration_payload("research@example.com", research_consent=True),
    )
    assert response.status_code == 201
    csrf = client.get("/auth/csrf").json()["token"]

    withdrawal = client.post(
        "/auth/research-consent/withdraw",
        headers={"X-CSRF-Token": csrf},
    )

    assert withdrawal.status_code == 200
    assert withdrawal.json()["user"]["research_consent"] is False
    db = session_factory()
    try:
        assert db.query(User).one().research_consent is False
    finally:
        db.close()


def test_protected_data_requires_privacy_notice_acknowledgment(deployment_client):
    client, _ = deployment_client
    user = User(
        id="legacy-user",
        email="legacy@example.com",
        password_hash="unused",
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_csrf] = lambda: None

    response = client.get("/transactions")

    assert response.status_code == 428
    app.dependency_overrides.pop(get_current_user)
    app.dependency_overrides.pop(require_csrf)


def test_production_requires_postgresql_database_url():
    code = "import backend.main"
    environment = os.environ.copy()
    environment.pop("DATABASE_URL", None)
    environment["APP_ENV"] = "production"
    missing = subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert missing.returncode != 0
    assert "DATABASE_URL is required" in missing.stderr

    environment["DATABASE_URL"] = "sqlite:///not-production.db"
    sqlite_production = subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert sqlite_production.returncode != 0
    assert "must point to PostgreSQL" in sqlite_production.stderr


def test_postgresql_url_is_normalized():
    code = "import backend.database; print(backend.database.SQLALCHEMY_DATABASE_URL)"
    environment = os.environ.copy()
    environment["APP_ENV"] = "production"
    environment["DATABASE_URL"] = "postgres://user:password@example.test/db"
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "postgresql+psycopg://user:password@example.test/db"


def test_existing_anomaly_artifacts_load():
    assert type(model).__name__ == "IsolationForest"
    assert len(category_stats.index) > 0
