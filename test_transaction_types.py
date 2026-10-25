from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth import get_current_user, require_csrf
from backend.database import Base, ensure_schema, get_db
from backend.main import app
from backend.models import Transaction, User
from backend.schemas import TransactionCreate


@pytest.fixture
def isolated_client():
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

    test_user = User(id="test-user", email="test@example.com", password_hash="unused")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_csrf] = lambda: None
    with TestClient(app) as client:
        yield client, session_factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def base_payload(transaction_type):
    return {
        "date": "2026-10-23",
        "name": f"Test {transaction_type}",
        "amount": 500,
        "account": "Savings",
        "type": transaction_type,
    }


def test_expense_and_income_require_categories_and_income_is_not_anomaly(isolated_client):
    client, session_factory = isolated_client

    invalid_expense = client.post("/transactions", json=base_payload("expense"))
    assert invalid_expense.status_code == 422

    invalid_income = client.post("/transactions", json=base_payload("income"))
    assert invalid_income.status_code == 422

    income = base_payload("income") | {"category": "Salary"}
    response = client.post("/transactions", json=income)
    assert response.status_code == 201
    assert response.json()["anomaly_status"] == "Not Applicable"
    assert response.json()["to_account"] is None

    db = session_factory()
    try:
        saved = db.query(Transaction).one()
        assert saved.category == "Salary"
        assert saved.type == "income"
    finally:
        db.close()


def test_transfer_requires_distinct_accounts_and_persists_both(isolated_client):
    client, session_factory = isolated_client
    payload = base_payload("transfer")

    missing_destination = client.post("/transactions", json=payload)
    assert missing_destination.status_code == 422

    same_accounts = payload | {"to_account": "Savings"}
    same_response = client.post("/transactions", json=same_accounts)
    assert same_response.status_code == 422

    transfer = payload | {"to_account": "Cash"}
    response = client.post("/transactions", json=transfer)
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "transfer"
    assert body["category"] == "Transfer"
    assert body["account"] == "Savings"
    assert body["to_account"] == "Cash"
    assert body["anomaly_status"] == "Not Applicable"

    listed = client.get("/transactions?type=transfer")
    assert listed.status_code == 200
    assert listed.json()["transactions"][0]["to_account"] == "Cash"

    db = session_factory()
    try:
        saved = db.query(Transaction).one()
        assert saved.account == "Savings"
        assert saved.to_account == "Cash"
    finally:
        db.close()


def test_existing_rows_survive_additive_migration():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY,
                    date DATE NOT NULL,
                    name VARCHAR NOT NULL,
                    amount FLOAT NOT NULL,
                    category VARCHAR NOT NULL,
                    account VARCHAR NOT NULL,
                    type VARCHAR NOT NULL,
                    note VARCHAR,
                    anomaly_status VARCHAR,
                    anomaly_score FLOAT,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO transactions
                (id, date, name, amount, category, account, type, created_at)
                VALUES (7, '2026-10-01', 'Old expense', 125, 'Food', 'Savings', 'expense', '2026-10-01 00:00:00')
                """
            )
        )

    ensure_schema(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("transactions")}
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT id, name, amount, account, to_account FROM transactions WHERE id = 7")
        ).one()

    assert "to_account" in columns
    assert tuple(row) == (7, "Old expense", 125.0, "Savings", None)


def test_transaction_create_schema_accepts_legacy_non_transfer_payload():
    payload = TransactionCreate(
        date=date(2026, 10, 23),
        name="Food",
        amount=100,
        category="Food",
        account="Savings",
        type="expense",
    )
    assert payload.to_account is None
