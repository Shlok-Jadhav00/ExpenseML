from datetime import date, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth import get_current_user
from backend.database import Base, get_db
from backend.main import app
from backend.model3_service import (
    TEMPORARY_TEST_MARKER,
    get_model3_transactions,
    predict_cashflow,
)
from backend.models import Transaction, User
from ml.model3.predictor import load_model_bundle, predict_next_7_days


@pytest.fixture
def isolated_client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    test_user = User(id="test-user", email="test@example.com", password_hash="unused")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as client:
        yield client, session_factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def add_rows(session_factory, rows):
    db = session_factory()
    try:
        for row in rows:
            if row.user_id is None:
                row.user_id = "test-user"
        db.add_all(rows)
        db.commit()
    finally:
        db.close()


def expense_rows(start_date=date(2026, 1, 1), days=35):
    return [
        Transaction(
            date=start_date + timedelta(days=index),
            name="Campus Canteen",
            amount=100 + index,
            category="Food",
            account="Savings",
            type="expense",
        )
        for index in range(days)
    ]


def test_artifact_loads_and_predictor_returns_model3_output():
    bundle = load_model_bundle()
    assert bundle["horizon_days"] == 7
    assert bundle["min_history_days"] == 28
    assert bundle["training_data_type"] == "synthetic"

    transactions = pd.DataFrame(
        [
            {
                "date": date(2026, 1, 1) + timedelta(days=index),
                "amount": 100 + index,
                "category": "Food",
                "type": "Expense",
            }
            for index in range(35)
        ]
    )
    result = predict_next_7_days(transactions, user_id="single_user")

    assert result["status"] == "ok"
    assert result["predicted_expense_next_7_days"] is not None
    assert result["warnings"]
    assert any("SYNTHETIC" in warning for warning in result["warnings"])


def test_sqlite_adapter_shape_cutoff_and_marker_exclusion(isolated_client):
    _, session_factory = isolated_client
    rows = expense_rows()
    rows.extend(
        [
            Transaction(
                date=date(2026, 2, 5),
                name="Future expense",
                amount=9999,
                category="Food",
                account="Savings",
                type="expense",
            ),
            Transaction(
                date=date(2026, 1, 10),
                name="Temporary test row",
                amount=500,
                category="Food",
                account="Savings",
                type="expense",
                note=TEMPORARY_TEST_MARKER,
            ),
        ]
    )
    add_rows(session_factory, rows)

    db = session_factory()
    try:
        frame = get_model3_transactions(db, user_id="test-user", forecast_date=date(2026, 2, 4))
    finally:
        db.close()

    assert list(frame.columns) == [
        "user_id",
        "date",
        "name",
        "amount",
        "category",
        "account",
        "type",
        "note",
    ]
    assert set(frame["user_id"]) == {"test-user"}
    assert frame["date"].max() == date(2026, 2, 4)
    assert TEMPORARY_TEST_MARKER not in frame["note"].fillna("").tolist()
    assert "Future expense" not in frame["name"].tolist()
    assert "Temporary test row" not in frame["name"].tolist()


def test_valid_forecast_serializes_and_does_not_write(isolated_client):
    client, session_factory = isolated_client
    add_rows(session_factory, expense_rows())
    db = session_factory()
    try:
        before_count = db.query(Transaction).count()
    finally:
        db.close()

    response = client.get("/cashflow-forecast?date=2026-02-04")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["user_id"] == "test-user"
    assert payload["forecast_date"] == "2026-02-04"
    assert payload["predicted_expense_next_7_days"] is not None
    assert payload["history_days"] == 35
    assert any("SYNTHETIC" in warning for warning in payload["warnings"])

    db = session_factory()
    try:
        assert db.query(Transaction).count() == before_count
    finally:
        db.close()


def test_forecast_cutoff_excludes_future_rows(isolated_client):
    _, session_factory = isolated_client
    rows = expense_rows()
    rows.append(
        Transaction(
            date=date(2026, 3, 1),
            name="Future expense",
            amount=10000,
            category="Food",
            account="Savings",
            type="expense",
        )
    )
    add_rows(session_factory, rows)

    db = session_factory()
    try:
        result = predict_cashflow(db, user_id="test-user", forecast_date=date(2026, 2, 4))
    finally:
        db.close()

    assert result["status"] == "ok"
    assert result["history_days"] == 35
    assert result["forecast_date"] == "2026-02-04"


def test_predictor_excludes_income_transfers_and_credit_card_repayments(isolated_client):
    _, session_factory = isolated_client
    rows = expense_rows()
    rows.extend(
        [
            Transaction(
                date=date(2026, 1, 5),
                name="Monthly allowance",
                amount=15000,
                category="Income",
                account="Savings",
                type="income",
            ),
            Transaction(
                date=date(2026, 1, 6),
                name="ATM transfer",
                amount=5000,
                category="Transfer",
                account="Savings",
                type="transfer",
            ),
            Transaction(
                date=date(2026, 1, 7),
                name="Credit Card Bill Payment",
                amount=7000,
                category="Bills",
                account="Savings",
                type="expense",
            ),
        ]
    )
    add_rows(session_factory, rows)

    db = session_factory()
    try:
        result = predict_cashflow(db, user_id="test-user", forecast_date=date(2026, 2, 4))
    finally:
        db.close()

    assert result["status"] == "ok"
    assert result["recent_week_expense"] < 1000


def test_no_data_and_insufficient_history_statuses(isolated_client):
    client, session_factory = isolated_client

    no_data = client.get("/cashflow-forecast?date=2026-02-04")
    assert no_data.status_code == 200
    assert no_data.json()["status"] == "no_data"

    add_rows(session_factory, expense_rows(days=5))
    insufficient = client.get("/cashflow-forecast?date=2026-01-05")
    assert insufficient.status_code == 200
    assert insufficient.json()["status"] == "insufficient_data"


def test_baseline_only_status_with_limited_history(isolated_client):
    client, session_factory = isolated_client
    add_rows(session_factory, expense_rows(days=14))

    response = client.get("/cashflow-forecast?date=2026-01-14")

    assert response.status_code == 200
    assert response.json()["status"] == "baseline_only"
    assert response.json()["predicted_expense_next_7_days"] is not None
