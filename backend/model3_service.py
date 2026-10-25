"""SQLite adapter for the isolated Model 3 cash-flow predictor."""

from datetime import date

import pandas as pd
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.models import Transaction
from ml.model3.predictor import predict_next_7_days

TEMPORARY_TEST_MARKER = "[TEMP_FORECAST_TEST_20261012]"
MODEL3_COLUMNS = [
    "user_id",
    "date",
    "name",
    "amount",
    "category",
    "account",
    "type",
    "note",
]


def get_model3_transactions(
    db: Session,
    user_id: str,
    forecast_date: date | None = None,
) -> pd.DataFrame:
    """Convert eligible SQLite rows to the predictor's required DataFrame."""
    query = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        or_(
            Transaction.note.is_(None),
            ~Transaction.note.contains(TEMPORARY_TEST_MARKER),
        )
    )
    if forecast_date is not None:
        query = query.filter(Transaction.date <= forecast_date)

    rows = query.order_by(Transaction.date, Transaction.id).all()
    return pd.DataFrame(
        [
            {
                "user_id": user_id,
                "date": row.date,
                "name": row.name,
                "amount": row.amount,
                "category": row.category,
                "account": row.account,
                "type": row.type,
                "note": row.note,
            }
            for row in rows
        ],
        columns=MODEL3_COLUMNS,
    )


def predict_cashflow(
    db: Session,
    user_id: str,
    forecast_date: date | None = None,
) -> dict:
    """Run Model 3 without writing to the database."""
    transactions = get_model3_transactions(db, user_id=user_id, forecast_date=forecast_date)
    return predict_next_7_days(
        transactions,
        user_id=user_id,
        forecast_date=forecast_date,
    )
