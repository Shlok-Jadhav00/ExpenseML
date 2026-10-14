from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app, get_historical_expense_amounts
from backend.models import Transaction
from ml.anomaly_model import analyze_expense, analyze_expense_with_history


@pytest.fixture
def isolated_client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, TestingSessionLocal
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def add_transactions(
    session,
    amounts,
    *,
    category="Food",
    transaction_type="expense",
    start_date=date(2026, 1, 1),
    anomaly_status=None,
):
    rows = [
        Transaction(
            date=start_date + timedelta(days=index),
            name=f"{category} test",
            amount=amount,
            category=category,
            account="Test Account",
            type=transaction_type,
            anomaly_status=anomaly_status,
        )
        for index, amount in enumerate(amounts)
    ]
    session.add_all(rows)
    session.commit()
    return rows


def test_global_fallback_remains_functional():
    result = analyze_expense(200, "Food")

    assert result["status"] == "Normal"
    assert "anomaly_score" in result


def test_insufficient_history_uses_global_provisional_fallback():
    result = analyze_expense_with_history(700, "Food", [100, 150, 200])

    assert result["message"].startswith("Global baseline used provisionally")
    assert result["scoring_method"] == "global_isolation_forest"
    assert "decision_function score" in result["message"]
    assert result["category_average"] == pytest.approx(303.10791366906477)


def test_personal_baselines_distinguish_low_and_high_spenders():
    low_history = [100, 120, 140, 160, 180, 200, 220, 240, 260, 280]
    high_history = [500, 540, 580, 620, 660, 700, 740, 760, 780, 800]

    low_result = analyze_expense_with_history(700, "Food", low_history)
    high_result = analyze_expense_with_history(700, "Food", high_history)

    assert low_result["status"] == "Anomaly"
    assert high_result["status"] == "Normal"
    assert low_result["scoring_method"] == "personal_modified_zscore"
    assert "Personal baseline used" in low_result["message"]
    assert "threshold margin" in low_result["message"]
    assert low_result["category_average"] == pytest.approx(sum(low_history) / 10)
    assert high_result["category_average"] == pytest.approx(sum(high_history) / 10)


def test_category_histories_are_independent():
    food_history = [100 + index * 10 for index in range(10)]
    shopping_history = [500 + index * 30 for index in range(10)]

    food_result = analyze_expense_with_history(700, "Food", food_history)
    food_without_shopping = analyze_expense_with_history(700, "Food", food_history)

    assert food_result == food_without_shopping
    assert analyze_expense_with_history(700, "Shopping", shopping_history)["status"] == "Normal"


def test_history_query_excludes_income_transfers_and_keeps_flagged_expenses(isolated_client):
    _, session_factory = isolated_client
    db = session_factory()
    try:
        add_transactions(db, [100, 120], category="Food", anomaly_status="Anomaly")
        add_transactions(
            db,
            [9000],
            category="Food",
            transaction_type="income",
            start_date=date(2026, 1, 10),
        )
        add_transactions(
            db,
            [8000],
            category="Food",
            transaction_type="transfer",
            start_date=date(2026, 1, 11),
        )
        add_transactions(
            db,
            [7000],
            category="Food",
            start_date=date(2026, 2, 1),
        )
        add_transactions(
            db,
            [9000],
            category="Shopping",
            start_date=date(2026, 1, 12),
        )

        amounts = get_historical_expense_amounts(db, "Food", date(2026, 1, 31))
    finally:
        db.close()

    assert amounts == [100.0, 120.0]


def test_transaction_is_classified_before_insertion(isolated_client):
    client, session_factory = isolated_client
    db = session_factory()
    try:
        add_transactions(
            db,
            [100, 120, 140, 160, 180, 200, 220, 240, 260, 280],
        )
        before_count = db.query(Transaction).count()
    finally:
        db.close()

    response = client.post(
        "/transactions",
        json={
            "date": "2026-01-11",
            "name": "Large Food Expense",
            "amount": 700,
            "category": "Food",
            "account": "Savings",
            "type": "expense",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["anomaly_status"] == "Anomaly"
    assert payload["scoring_method"] == "personal_modified_zscore"

    db = session_factory()
    try:
        assert db.query(Transaction).count() == before_count + 1
        saved = db.get(Transaction, payload["id"])
        assert saved.amount == 700
    finally:
        db.close()


def test_analyze_uses_history_without_mutating_database(isolated_client):
    client, session_factory = isolated_client
    db = session_factory()
    try:
        add_transactions(
            db,
            [100, 120, 140, 160, 180, 200, 220, 240, 260, 280],
        )
        before_count = db.query(Transaction).count()
    finally:
        db.close()

    response = client.post(
        "/analyze",
        json={"amount": 700, "category": "Food"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Anomaly"
    assert response.json()["scoring_method"] == "personal_modified_zscore"
    assert "Personal baseline used" in response.json()["message"]

    db = session_factory()
    try:
        assert db.query(Transaction).count() == before_count
    finally:
        db.close()


def test_income_and_transfer_keep_not_applicable(isolated_client):
    client, session_factory = isolated_client

    for transaction_type in ("income", "transfer"):
        response = client.post(
            "/transactions",
            json={
                "date": "2026-01-01",
                "name": f"Test {transaction_type}",
                "amount": 10000,
                "category": "Food",
                "account": "Savings",
                "type": transaction_type,
            },
        )
        assert response.status_code == 201
        assert response.json()["anomaly_status"] == "Not Applicable"
        assert response.json()["scoring_method"] == "not_applicable"

    db = session_factory()
    try:
        assert get_historical_expense_amounts(db, "Food", date(2026, 1, 2)) == []
    finally:
        db.close()


def test_statistical_edge_cases_are_safe():
    constant = analyze_expense_with_history(700, "Food", [200] * 10)
    zero_mad_with_variation = analyze_expense_with_history(
        700,
        "Food",
        [100] * 8 + [200] * 2,
    )
    unknown = analyze_expense_with_history(700, "Unknown", [])
    invalid = analyze_expense_with_history(0, "Food", [100] * 10)

    assert "no usable variation" in constant["message"]
    assert "fallback scale" in zero_mad_with_variation["message"]
    assert unknown["status"] == "Unknown"
    assert invalid["status"] == "Unknown"


def test_crud_and_forecast_endpoints_still_work(isolated_client):
    client, session_factory = isolated_client
    db = session_factory()
    try:
        add_transactions(
            db,
            [100 + index * 5 for index in range(29)],
            start_date=date(2026, 9, 14),
        )
    finally:
        db.close()

    create_response = client.post(
        "/transactions",
        json={
            "date": "2026-10-13",
            "name": "CRUD Test",
            "amount": 200,
            "category": "Shopping",
            "account": "Cash",
            "type": "expense",
        },
    )
    assert create_response.status_code == 201
    transaction_id = create_response.json()["id"]

    listed = client.get("/transactions")
    fetched = client.get(f"/transactions/{transaction_id}")
    forecast = client.get("/forecast?date=2026-10-13")
    deleted = client.delete(f"/transactions/{transaction_id}")
    missing = client.get(f"/transactions/{transaction_id}")

    assert listed.status_code == 200
    assert fetched.status_code == 200
    assert forecast.status_code == 200
    assert forecast.json()["feature_date"] == "2026-10-12"
    assert deleted.status_code == 204
    assert missing.status_code == 404
