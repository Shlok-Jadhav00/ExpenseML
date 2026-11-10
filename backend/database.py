"""
SQLAlchemy database engine, session factory, and dependency.

The SQLite database file is stored at ``data/expenses.db`` relative to the
project root.  Tables are created automatically on first import.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ---------------------------------------------------------------------------
# Database location — ``data/expenses.db`` at the project root
# Override with DATABASE_URL env var for isolated testing.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _PROJECT_ROOT / "data" / "expenses.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _database_url() -> str:
    configured_url = os.getenv("DATABASE_URL")
    if os.getenv("APP_ENV", "development").lower() == "production" and not configured_url:
        raise RuntimeError("DATABASE_URL is required when APP_ENV=production")

    url = configured_url or f"sqlite:///{_DB_PATH}"
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if (
        os.getenv("APP_ENV", "development").lower() == "production"
        and not url.startswith("postgresql+psycopg://")
    ):
        raise RuntimeError("Production DATABASE_URL must point to PostgreSQL")
    return url


SQLALCHEMY_DATABASE_URL = _database_url()
_ENGINE_KWARGS = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    _ENGINE_KWARGS["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    **_ENGINE_KWARGS,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def ensure_schema(database_engine=engine):
    """Apply additive changes without recreating or deleting data."""
    inspector = inspect(database_engine)
    tables = set(inspector.get_table_names())
    transaction_columns = {
        column["name"] for column in inspector.get_columns("transactions")
    }
    user_columns = (
        {column["name"] for column in inspector.get_columns("users")}
        if "users" in tables
        else set()
    )
    additions = []
    if "to_account" not in transaction_columns:
        additions.append(("transactions", "to_account VARCHAR"))
    if "user_id" not in transaction_columns:
        additions.append(("transactions", "user_id VARCHAR(36)"))
    if "users" in tables and "privacy_notice_version" not in user_columns:
        additions.append(("users", "privacy_notice_version VARCHAR(32)"))
    if "users" in tables and "privacy_notice_accepted_at" not in user_columns:
        additions.append(("users", "privacy_notice_accepted_at TIMESTAMP"))
    if "users" in tables and "research_consent" not in user_columns:
        additions.append(("users", "research_consent BOOLEAN DEFAULT FALSE"))
    if "users" in tables and "research_consent_version" not in user_columns:
        additions.append(("users", "research_consent_version VARCHAR(32)"))
    if "users" in tables and "research_consent_at" not in user_columns:
        additions.append(("users", "research_consent_at TIMESTAMP"))
    with database_engine.begin() as connection:
        for table_name, definition in additions:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {definition}"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_transactions_user_date ON transactions (user_id, date)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_transactions_user_category ON transactions (user_id, category)")
        )


def get_db():
    """FastAPI dependency that yields a database session and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
