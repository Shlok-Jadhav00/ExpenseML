"""
FastAPI backend for the Expense Intelligence anomaly detection system.

Exposes the trained IsolationForest model via a REST API and provides
CRUD endpoints for transaction storage backed by SQLite.

The ML logic lives in ml/anomaly_model.py — this module only wraps it.
"""

from datetime import date, timedelta

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models import Transaction
from backend.schemas import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    ForecastResponse,
)
from ml.anomaly_model import analyze_expense_with_history
from ml.forecasting_model import predict_next_day_expense

# ---------------------------------------------------------------------------
# Create tables on startup
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

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


def get_historical_expense_amounts(
    db: Session,
    category: str,
    target_date: date,
) -> list[float]:
    """Return prior expense amounts for one category and target date."""
    rows = (
        db.query(Transaction.amount)
        .filter(
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
            Transaction.type == "expense",
            Transaction.date <= feature_date,
        )
        .group_by(Transaction.date)
        .order_by(Transaction.date)
        .all()
    )
    daily_totals = pd.DataFrame(rows, columns=["date", "daily_expense"])
    return predict_next_day_expense(daily_totals, prediction_date)


# ---------------------------------------------------------------------------
# Anomaly analysis endpoint (stateless — unchanged from v0.1)
# ---------------------------------------------------------------------------

@app.post("/analyze", response_model=AnalysisResponse)
def analyze(
    expense: ExpenseRequest,
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
        date=payload.date_,
        name=payload.name,
        amount=payload.amount,
        category=payload.category,
        account=payload.account,
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
    db: Session = Depends(get_db),
) -> dict:
    """List transactions with optional filters and pagination."""
    query = db.query(Transaction)

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
    db: Session = Depends(get_db),
) -> Transaction:
    """Retrieve a single transaction by its ID."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@app.delete("/transactions/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a transaction by its ID."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(transaction)
    db.commit()
