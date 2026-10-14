from datetime import date, timedelta

import numpy as np
import pandas as pd

import ml.forecasting_model as forecasting


def make_daily_totals(start: date, periods: int) -> pd.DataFrame:
    dates = pd.date_range(start=start, periods=periods, freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "daily_expense": np.arange(100, 100 + periods, dtype=float),
        }
    )


def notebook_features(daily_totals: pd.DataFrame) -> pd.DataFrame:
    reference = daily_totals.copy()
    reference["date"] = pd.to_datetime(reference["date"])
    reference["lag_1"] = reference["daily_expense"].shift(1)
    reference["lag_2"] = reference["daily_expense"].shift(2)
    reference["lag_3"] = reference["daily_expense"].shift(3)
    reference["lag_7"] = reference["daily_expense"].shift(7)
    reference["lag_14"] = reference["daily_expense"].shift(14)
    reference["lag_28"] = reference["daily_expense"].shift(28)
    reference["rolling_3"] = reference["daily_expense"].rolling(3).mean().shift(1)
    reference["rolling_7"] = reference["daily_expense"].rolling(7).mean().shift(1)
    reference["rolling_14"] = reference["daily_expense"].rolling(14).mean().shift(1)
    reference["rolling_28"] = reference["daily_expense"].rolling(28).mean().shift(1)
    reference["day_of_week"] = reference["date"].dt.dayofweek
    reference["day_of_month"] = reference["date"].dt.day
    reference["month"] = reference["date"].dt.month
    reference["is_weekend"] = (reference["day_of_week"] >= 5).astype(int)
    reference["day_number"] = np.arange(len(reference))
    reference["target"] = reference["daily_expense"].shift(-1)
    return reference.dropna().reset_index(drop=True)


def test_notebook_alignment() -> None:
    daily_totals = make_daily_totals(date(2025, 10, 1), 365)
    reference = notebook_features(daily_totals)
    reference_index = 100
    feature_date = reference.loc[reference_index, "date"].date()
    prediction_date = feature_date + timedelta(days=1)

    generated = forecasting.build_forecast_features(daily_totals, prediction_date)
    expected = reference.loc[[reference_index], forecasting.EXPECTED_FEATURES]

    assert generated.values is not None
    pd.testing.assert_frame_equal(
        generated.values,
        expected.reset_index(drop=True),
        check_dtype=False,
    )
    assert generated.feature_date == feature_date
    assert generated.prediction_date == prediction_date
    assert generated.values["day_number"].iloc[0] == expected["day_number"].iloc[0]


def test_future_data_is_ignored() -> None:
    daily_totals = make_daily_totals(date(2025, 10, 1), 40)
    prediction_date = date(2025, 11, 10)
    baseline = forecasting.build_forecast_features(daily_totals, prediction_date)

    future = pd.DataFrame(
        {
            "date": [pd.Timestamp(prediction_date), pd.Timestamp("2025-11-11")],
            "daily_expense": [999999.0, 999999.0],
        }
    )
    with_future = forecasting.build_forecast_features(
        pd.concat([daily_totals, future], ignore_index=True),
        prediction_date,
    )

    assert baseline.values is not None
    assert with_future.values is not None
    pd.testing.assert_frame_equal(baseline.values, with_future.values)


def test_minimum_history_does_not_call_model() -> None:
    daily_totals = make_daily_totals(date(2025, 10, 1), 28)
    original_model = forecasting.model

    class FailingModel:
        def predict(self, _features: pd.DataFrame) -> None:
            raise AssertionError("Model must not be called with insufficient history")

    forecasting.model = FailingModel()
    try:
        result = forecasting.predict_next_day_expense(
            daily_totals,
            date(2025, 10, 29),
        )
    finally:
        forecasting.model = original_model

    assert result["status"] == "Insufficient Data"
    assert result["predicted_amount"] is None
    assert result["days_of_history"] == 28

    exact_minimum = forecasting.build_forecast_features(
        make_daily_totals(date(2025, 10, 1), 29),
        date(2025, 10, 30),
    )
    assert exact_minimum.values is not None
    assert exact_minimum.days_of_history == 29


def test_gap_filling_and_day_number_limit() -> None:
    daily_totals = make_daily_totals(date(2025, 10, 1), 400)
    daily_totals = daily_totals.drop(index=10).reset_index(drop=True)
    explicit_zero = make_daily_totals(date(2025, 10, 1), 400)
    explicit_zero.loc[10, "daily_expense"] = 0
    prediction_date = date(2026, 11, 5)
    generated_gap = forecasting.build_forecast_features(
        daily_totals,
        prediction_date,
    )
    generated_zero = forecasting.build_forecast_features(
        explicit_zero,
        prediction_date,
    )
    assert generated_gap.values is not None
    assert generated_zero.values is not None
    pd.testing.assert_frame_equal(generated_gap.values, generated_zero.values)

    result = forecasting.predict_next_day_expense(
        daily_totals,
        prediction_date,
    )

    assert result["status"] == "OK"
    assert result["days_of_history"] == 400
    assert result["message"] is not None
    assert "outside the model's synthetic training range" in result["message"]


if __name__ == "__main__":
    test_notebook_alignment()
    test_future_data_is_ignored()
    test_minimum_history_does_not_call_model()
    test_gap_filling_and_day_number_limit()
    print("Forecasting alignment and behavior tests passed.")