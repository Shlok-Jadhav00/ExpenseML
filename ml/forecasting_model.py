"""Inference utilities for the experimental Model 2 expense forecast."""

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
EXPECTED_FEATURES = [
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_7",
    "lag_14",
    "lag_28",
    "rolling_3",
    "rolling_7",
    "rolling_14",
    "rolling_28",
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "day_number",
]
EXPERIMENTAL_MESSAGE = (
    "Experimental forecast: this model was trained on synthetic spending data "
    "and has not been validated on real-world financial data."
)
TRAINING_DAY_NUMBER_MIN = 28
TRAINING_DAY_NUMBER_MAX = 363

model = joblib.load(BASE_DIR / "expense_forecasting_model.pkl")
feature_names = joblib.load(BASE_DIR / "expense_forecasting_features.pkl")

if feature_names != EXPECTED_FEATURES:
    raise ValueError(
        "Forecasting artifact feature order does not match the training contract."
    )


@dataclass
class ForecastFeatures:
    """Generated feature row and metadata for one forecast target date."""

    values: pd.DataFrame | None
    prediction_date: date
    feature_date: date
    first_date: date | None
    days_of_history: int
    message: str | None


def _as_date(value: date | pd.Timestamp) -> date:
    """Normalize supported date-like values to a calendar date."""
    if isinstance(value, pd.Timestamp):
        return value.date()
    return value


def build_forecast_features(
    daily_totals: pd.DataFrame,
    prediction_date: date,
) -> ForecastFeatures:
    """Build the exact 15-feature row used to predict ``prediction_date``.

    The feature row is dated one day before the target, matching the notebook's
    shifted target construction.
    """
    feature_date = prediction_date - timedelta(days=1)
    required_columns = {"date", "daily_expense"}
    if not required_columns.issubset(daily_totals.columns):
        missing = required_columns - set(daily_totals.columns)
        raise ValueError(f"daily_totals is missing columns: {sorted(missing)}")

    daily = daily_totals[["date", "daily_expense"]].copy()
    daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
    cutoff = pd.Timestamp(feature_date)
    daily = daily[daily["date"] <= cutoff]

    if daily.empty:
        return ForecastFeatures(
            values=None,
            prediction_date=prediction_date,
            feature_date=feature_date,
            first_date=None,
            days_of_history=0,
            message="No expense history is available before the prediction date.",
        )

    daily = (
        daily.groupby("date", as_index=False)["daily_expense"]
        .sum()
        .sort_values("date")
    )
    first_date = daily["date"].iloc[0].date()
    full_dates = pd.date_range(first_date, cutoff, freq="D")
    daily = (
        daily.set_index("date")
        .reindex(full_dates, fill_value=0)
        .rename_axis("date")
        .reset_index()
    )

    elapsed_days = (feature_date - first_date).days
    days_of_history = len(full_dates)
    if elapsed_days < TRAINING_DAY_NUMBER_MIN:
        return ForecastFeatures(
            values=None,
            prediction_date=prediction_date,
            feature_date=feature_date,
            first_date=first_date,
            days_of_history=days_of_history,
            message=(
                "At least 29 inclusive calendar-date rows are required: "
                "the feature date must be at least 28 elapsed days after "
                "the first available date."
            ),
        )

    daily["lag_1"] = daily["daily_expense"].shift(1)
    daily["lag_2"] = daily["daily_expense"].shift(2)
    daily["lag_3"] = daily["daily_expense"].shift(3)
    daily["lag_7"] = daily["daily_expense"].shift(7)
    daily["lag_14"] = daily["daily_expense"].shift(14)
    daily["lag_28"] = daily["daily_expense"].shift(28)
    daily["rolling_3"] = daily["daily_expense"].rolling(3).mean().shift(1)
    daily["rolling_7"] = daily["daily_expense"].rolling(7).mean().shift(1)
    daily["rolling_14"] = daily["daily_expense"].rolling(14).mean().shift(1)
    daily["rolling_28"] = daily["daily_expense"].rolling(28).mean().shift(1)
    daily["day_of_week"] = daily["date"].dt.dayofweek
    daily["day_of_month"] = daily["date"].dt.day
    daily["month"] = daily["date"].dt.month
    daily["is_weekend"] = (daily["day_of_week"] >= 5).astype(int)
    daily["day_number"] = np.arange(len(daily))

    feature_row = daily.loc[daily["date"] == cutoff, feature_names]
    if feature_row.empty or feature_row.isna().any(axis=None):
        raise ValueError("Unable to generate complete forecasting features.")

    messages = [EXPERIMENTAL_MESSAGE]
    day_number = int(feature_row["day_number"].iloc[0])
    if not TRAINING_DAY_NUMBER_MIN <= day_number <= TRAINING_DAY_NUMBER_MAX:
        messages.append(
            "The day_number is outside the model's synthetic training range "
            "of 28 through 363; forecast reliability may be reduced."
        )

    return ForecastFeatures(
        values=feature_row.reset_index(drop=True),
        prediction_date=prediction_date,
        feature_date=feature_date,
        first_date=first_date,
        days_of_history=days_of_history,
        message=" ".join(messages),
    )


def predict_next_day_expense(
    daily_totals: pd.DataFrame,
    prediction_date: date,
) -> dict:
    """Return an experimental next-day expense forecast."""
    generated = build_forecast_features(daily_totals, prediction_date)
    if generated.values is None:
        return {
            "status": "Insufficient Data",
            "predicted_amount": None,
            "prediction_date": generated.prediction_date,
            "feature_date": generated.feature_date,
            "days_of_history": generated.days_of_history,
            "message": generated.message,
        }

    prediction = float(model.predict(generated.values)[0])
    return {
        "status": "OK",
        "predicted_amount": prediction,
        "prediction_date": generated.prediction_date,
        "feature_date": generated.feature_date,
        "days_of_history": generated.days_of_history,
        "message": generated.message,
    }
