"""
FastAPI backend for the Expense Intelligence anomaly detection system.

Exposes the trained IsolationForest model via a REST API and provides
CRUD endpoints for transaction storage backed by SQLite.

The ML logic lives in ml/anomaly_model.py — this module only wraps it.
"""

from datetime import date, timedelta
from uuid import uuid4

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import Base, engine, ensure_schema, get_db
from backend.models import Transaction
from backend.schemas import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    ForecastResponse,
    CashflowForecastResponse,
)
from backend.model3_service import predict_cashflow
from backend.auth import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    create_session,
    enforce_rate_limit,
    get_current_session,
    get_current_user,
    hash_password,
    require_csrf,
    session_csrf_token,
    set_session_cookie,
    utc_now,
    validate_request_origin,
    verify_password,
)
from backend.models import User, UserSession
from backend.schemas import (
    AuthResponse,
    AuthUserResponse,
    CsrfResponse,
    LoginRequest,
    ReauthenticateRequest,
    RegisterRequest,
)
from ml.anomaly_model import analyze_expense_with_history
from ml.forecasting_model import predict_next_day_expense

# ---------------------------------------------------------------------------
# Create tables on startup
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)
ensure_schema(engine)

# ---------------------------------------------------------------------------
# Pydantic models for the existing /analyze endpoint
# ---------------------------------------------------------------------------

class ExpenseRequest(BaseModel):
    """Incoming expense to analyze."""
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    category: str = Field(..., min_length=1, description="Spending category, e.g. Food, Shopping")


class AnalysisResponse(BaseModel):
    """Structured anomaly-detection result."""
    status: str
    anomaly_score: float | None = None
    category_average: float | None = None
    category_zscore: float | None = None
    scoring_method: str | None = None
    message: str | None = None


TRANSFER_CATEGORY = "Transfer"


def get_historical_expense_amounts(
    db: Session,
    user_id: str,
    category: str,
    target_date: date,
) -> list[float]:
    """Return prior expense amounts for one category and target date."""
    rows = (
        db.query(Transaction.amount)
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.category == category,
            Transaction.date <= target_date,
        )
        .order_by(Transaction.date, Transaction.id)
        .all()
    )
    return [float(amount) for (amount,) in rows]


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Expense Intelligence API",
    description="Analyzes spending behavior and detects anomalous transactions.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _auth_response(user: User) -> dict:
    return {"user": {"id": user.id, "email": user.email}}


@app.post("/auth/register", response_model=AuthResponse, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    validate_request_origin(request)
    enforce_rate_limit(request, "register")
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=400, detail="Unable to register with those details")

    user = User(id=str(uuid4()), email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    _, raw_token = create_session(db, user)
    db.commit()
    set_session_cookie(response, raw_token)
    return _auth_response(user)


@app.post("/auth/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    validate_request_origin(request)
    enforce_rate_limit(request, "login")
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    _, raw_token = create_session(db, user)
    db.commit()
    set_session_cookie(response, raw_token)
    return _auth_response(user)


@app.get("/auth/me", response_model=AuthResponse)
def auth_me(user: User = Depends(get_current_user)) -> dict:
    return _auth_response(user)


@app.get("/auth/csrf", response_model=CsrfResponse)
def csrf_token(
    db: Session = Depends(get_db),
    session: UserSession = Depends(get_current_session),
) -> dict:
    return {"token": session_csrf_token(session, db)}


@app.post("/auth/logout", status_code=204)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    session: UserSession = Depends(get_current_session),
    _: None = Depends(require_csrf),
) -> Response:
    session.revoked_at = utc_now()
    db.commit()
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.delete("/auth/account", status_code=204)
def delete_account(
    payload: ReauthenticateRequest,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> Response:
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=403, detail="Recent password reauthentication required")
    db.query(Transaction).filter(Transaction.user_id == user.id).delete(synchronize_session=False)
    db.query(UserSession).filter(UserSession.user_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


# ---------------------------------------------------------------------------
# General endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root() -> dict:
    """Root endpoint — basic API information."""
    return {
        "application": "Expense Intelligence API",
        "version": "0.2.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/forecast", response_model=ForecastResponse)
def forecast(
    forecast_date: date | None = Query(
        None,
        alias="date",
        description="Target date to predict; defaults to tomorrow",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return an experimental next-day spending forecast from stored expenses."""
    prediction_date = forecast_date or (date.today() + timedelta(days=1))
    if prediction_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Forecast date must be today or a future date",
        )

    feature_date = prediction_date - timedelta(days=1)
    rows = (
        db.query(
            Transaction.date,
            func.sum(Transaction.amount).label("daily_expense"),
        )
        .filter(
            Transaction.user_id == user.id,
            Transaction.type == "expense",
            Transaction.date <= feature_date,
        )
        .group_by(Transaction.date)
        .order_by(Transaction.date)
        .all()
    )
    daily_totals = pd.DataFrame(rows, columns=["date", "daily_expense"])
    return predict_next_day_expense(daily_totals, prediction_date)


@app.get("/cashflow-forecast", response_model=CashflowForecastResponse)
def cashflow_forecast(
    forecast_date: date | None = Query(
        None,
        alias="date",
        description="Forecast cutoff date; defaults to the latest recorded date",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the isolated Model 3 seven-day expense forecast."""
    try:
        return predict_cashflow(db, user_id=user.id, forecast_date=forecast_date)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Cash-flow forecast failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Anomaly analysis endpoint (stateless — unchanged from v0.1)
# ---------------------------------------------------------------------------

@app.post("/analyze", response_model=AnalysisResponse)
def analyze(
    expense: ExpenseRequest,
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """
    Analyze a single expense for anomalies.

    Uses personal category history when available and otherwise falls back
    to the trained IsolationForest model.
    """
    try:
        historical_amounts = get_historical_expense_amounts(
            db,
            user.id,
            expense.category,
            date.today(),
        )
        result = analyze_expense_with_history(
            expense.amount,
            expense.category,
            historical_amounts,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Model inference failed: {exc}",
        ) from exc

    return AnalysisResponse(**result)


# ---------------------------------------------------------------------------
# Transaction CRUD endpoints
# ---------------------------------------------------------------------------

@app.post("/transactions", response_model=TransactionResponse, status_code=201)
def create_transaction(
    payload: TransactionCreate,
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """
    Create a new transaction and persist it to the database.

    Anomaly detection is only run for transactions of type ``"expense"``.
    For ``"income"`` and ``"transfer"`` the anomaly status is set to
    ``"Not Applicable"``.
    """
    anomaly_status: str | None = None
    anomaly_score: float | None = None
    scoring_method: str | None = None

    if payload.type_ == "expense":
        try:
            historical_amounts = get_historical_expense_amounts(
                db,
                user.id,
                payload.category,
                payload.date_,
            )
            result = analyze_expense_with_history(
                payload.amount,
                payload.category,
                historical_amounts,
            )
            anomaly_status = result.get("status")
            anomaly_score = result.get("anomaly_score")
            scoring_method = result.get("scoring_method")
        except Exception:
            anomaly_status = "Error"
            scoring_method = "error"
    else:
        anomaly_status = "Not Applicable"
        scoring_method = "not_applicable"

    transaction = Transaction(
        user_id=user.id,
        date=payload.date_,
        name=payload.name,
        amount=payload.amount,
        category=payload.category if payload.type_ != "transfer" else TRANSFER_CATEGORY,
        account=payload.account,
        to_account=payload.to_account,
        type=payload.type_,
        note=payload.note,
        anomaly_status=anomaly_status,
        anomaly_score=anomaly_score,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    response = TransactionResponse.model_validate(transaction)
    return response.model_copy(update={"scoring_method": scoring_method})


@app.get("/transactions", response_model=TransactionListResponse)
def list_transactions(
    category: str | None = Query(None, description="Filter by category"),
    type: str | None = Query(None, description="Filter by type"),
    account: str | None = Query(None, description="Filter by account"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List transactions with optional filters and pagination."""
    query = db.query(Transaction).filter(Transaction.user_id == user.id)

    if category is not None:
        query = query.filter(Transaction.category == category)
    if type is not None:
        query = query.filter(Transaction.type == type)
    if account is not None:
        query = query.filter(Transaction.account == account)

    total = query.count()
    transactions = (
        query.order_by(Transaction.date.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {"count": total, "transactions": transactions}


@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Transaction:
    """Retrieve a single transaction by its ID."""
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@app.delete("/transactions/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: int,
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> None:
    """Delete a transaction by its ID."""
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(transaction)
    db.commit()
