"""
Pydantic schemas for request validation and response serialization.

Keeps the API contract separate from the ORM models.
"""

from datetime import date as date_type, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Transaction schemas
# ---------------------------------------------------------------------------

class TransactionCreate(BaseModel):
    """Request body for creating a new transaction."""

    date_: date_type = Field(..., alias="date", description="Transaction date (YYYY-MM-DD)")
    name: str = Field(..., min_length=1, description="Merchant or payee name")
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    category: str = Field(..., min_length=1, description="Spending category, e.g. Food, Shopping")
    account: str = Field(..., min_length=1, description="Account used, e.g. Savings, Cash")
    type_: Literal["income", "expense", "transfer"] = Field(
        ..., alias="type", description="Transaction type",
    )
    note: str | None = Field(None, description="Optional note about the transaction")

    model_config = ConfigDict(populate_by_name=True)


class TransactionResponse(BaseModel):
    """A stored transaction with its anomaly analysis result."""

    id: int
    date_: date_type = Field(..., alias="date")
    name: str
    amount: float
    category: str
    account: str
    type_: str = Field(..., alias="type")
    note: str | None
    anomaly_status: str | None
    anomaly_score: float | None
    scoring_method: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TransactionListResponse(BaseModel):
    """Paginated list of transactions."""

    count: int
    transactions: list[TransactionResponse]


class ForecastResponse(BaseModel):
    """Experimental next-day spending prediction result."""

    status: str
    predicted_amount: float | None
    prediction_date: date_type
    feature_date: date_type
    days_of_history: int
    message: str | None = None
