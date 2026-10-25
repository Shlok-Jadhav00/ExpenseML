"""
Pydantic schemas for request validation and response serialization.

Keeps the API contract separate from the ORM models.
"""

from datetime import date as date_type, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Transaction schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=128)


class ReauthenticateRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)


class AuthUserResponse(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    user: AuthUserResponse


class CsrfResponse(BaseModel):
    token: str

class TransactionCreate(BaseModel):
    """Request body for creating a new transaction."""

    date_: date_type = Field(..., alias="date", description="Transaction date (YYYY-MM-DD)")
    name: str = Field(..., min_length=1, description="Merchant or payee name")
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    category: str | None = Field(None, min_length=1, description="Category for expenses and income")
    account: str = Field(..., min_length=1, description="Account used, e.g. Savings, Cash")
    to_account: str | None = Field(None, alias="to_account", min_length=1, description="Destination account for transfers")
    type_: Literal["income", "expense", "transfer"] = Field(
        ..., alias="type", description="Transaction type",
    )
    note: str | None = Field(None, description="Optional note about the transaction")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_transaction_fields(self):
        if not self.account.strip():
            raise ValueError("Source account is required")

        if self.type_ in {"expense", "income"}:
            if not self.category or not self.category.strip():
                raise ValueError("Category is required for expense and income transactions")
            if self.to_account is not None:
                raise ValueError("Destination account is only valid for transfers")
        else:
            if not self.to_account or not self.to_account.strip():
                raise ValueError("Destination account is required for transfers")
            if self.account.strip() == self.to_account.strip():
                raise ValueError("Source and destination accounts must be different")
            if self.category is not None and self.category.strip():
                raise ValueError("Category must be omitted for transfers")

        return self


class TransactionResponse(BaseModel):
    """A stored transaction with its anomaly analysis result."""

    id: int
    date_: date_type = Field(..., alias="date")
    name: str
    amount: float
    category: str
    account: str
    to_account: str | None = None
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


class CashflowForecastResponse(BaseModel):
    """Model 3 seven-day cash-flow forecast response."""

    user_id: str
    status: str
    message: str
    forecast_date: str | None = None
    prediction_period: str | None = None
    predicted_expense_next_7_days: float | None = None
    typical_range: tuple[float, float] | None = None
    recent_week_expense: float | None = None
    difference_from_recent_week_pct: float | None = None
    history_days: int
    model_used: str | None = None
    month_to_date_expense: float | None = None
    estimated_rest_of_month_expense: float | None = None
    observations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
