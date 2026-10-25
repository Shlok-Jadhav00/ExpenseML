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

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DB_PATH}")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def ensure_schema(database_engine=engine):
    """Apply additive SQLite changes without recreating or deleting data."""
    transaction_columns = {
        column["name"]
        for column in inspect(database_engine).get_columns("transactions")
    }
    if "to_account" not in transaction_columns:
        with database_engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE transactions ADD COLUMN to_account VARCHAR")
            )
    if "user_id" not in transaction_columns:
        with database_engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE transactions ADD COLUMN user_id VARCHAR(36)")
            )
    with database_engine.begin() as connection:
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
