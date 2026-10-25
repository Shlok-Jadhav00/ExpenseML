from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.models import Transaction, User


def make_client():
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
    return TestClient(app), session_factory, engine


def register(client, email, password):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    csrf = client.get("/auth/csrf")
    assert csrf.status_code == 200
    return csrf.json()["token"]


def login(client, email, password):
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    csrf = client.get("/auth/csrf")
    assert csrf.status_code == 200
    return csrf.json()["token"]


def transaction_payload(name, amount):
    return {
        "date": "2026-10-23",
        "name": name,
        "amount": amount,
        "category": "Food",
        "account": "Savings",
        "type": "expense",
    }


def test_users_are_isolated_and_client_ids_are_ignored():
    client_a, session_factory, engine = make_client()
    client_b = TestClient(app)
    try:
        csrf_a = register(client_a, "alice@example.com", "alice-password-123")
        response_a = client_a.post(
            "/transactions",
            json=transaction_payload("Alice expense", 100) | {"user_id": "someone-else"},
            headers={"X-CSRF-Token": csrf_a},
        )
        assert response_a.status_code == 201
        transaction_a = response_a.json()["id"]

        csrf_b = register(client_b, "bob@example.com", "bob-password-123")
        response_b = client_b.post(
            "/transactions",
            json=transaction_payload("Bob expense", 900),
            headers={"X-CSRF-Token": csrf_b},
        )
        assert response_b.status_code == 201
        transaction_b = response_b.json()["id"]

        assert [row["name"] for row in client_a.get("/transactions").json()["transactions"]] == ["Alice expense"]
        assert [row["name"] for row in client_b.get("/transactions").json()["transactions"]] == ["Bob expense"]
        assert client_a.get(f"/transactions/{transaction_b}").status_code == 404
        assert client_a.delete(
            f"/transactions/{transaction_b}",
            headers={"X-CSRF-Token": csrf_a},
        ).status_code == 404

        db = session_factory()
        try:
            saved = db.get(Transaction, transaction_a)
            assert saved.user_id is not None
            assert saved.user_id != "someone-else"
            user = db.get(User, saved.user_id)
            assert user.password_hash != "alice-password-123"
        finally:
            db.close()
    finally:
        client_a.close()
        client_b.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_csrf_logout_revocation_and_account_deletion():
    client, session_factory, engine = make_client()
    try:
        csrf = register(client, "delete@example.com", "delete-password-123")
        assert client.post(
            "/transactions",
            json=transaction_payload("Delete me", 100),
            headers={"X-CSRF-Token": "invalid"},
        ).status_code == 403
        created = client.post(
            "/transactions",
            json=transaction_payload("Delete me", 100),
            headers={"X-CSRF-Token": csrf},
        )
        assert created.status_code == 201

        logout = client.post("/auth/logout", headers={"X-CSRF-Token": csrf})
        assert logout.status_code == 204
        assert client.get("/transactions").status_code == 401

        csrf = login(client, "delete@example.com", "delete-password-123")
        deleted = client.request(
            "DELETE",
            "/auth/account",
            json={"password": "delete-password-123"},
            headers={"X-CSRF-Token": csrf},
        )
        assert deleted.status_code == 204
        assert client.get("/auth/me").status_code == 401

        db = session_factory()
        try:
            assert db.query(User).count() == 0
            assert db.query(Transaction).count() == 0
        finally:
            db.close()
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_legacy_unassigned_rows_are_not_visible():
    client, session_factory, engine = make_client()
    try:
        db = session_factory()
        db.add(
            Transaction(
                date=date(2026, 10, 1),
                name="Legacy row",
                amount=100,
                category="Food",
                account="Savings",
                type="expense",
                user_id=None,
            )
        )
        db.commit()
        db.close()

        register(client, "legacy@example.com", "legacy-password-123")
        payload = client.get("/transactions").json()
        assert payload["count"] == 0
        assert payload["transactions"] == []
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
