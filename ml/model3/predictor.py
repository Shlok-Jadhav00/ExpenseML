"""SpendSense Model 3 inference helper (aligned with the included notebook).

Input: a pandas DataFrame of transaction rows and a user ID.
Output: a dictionary containing a seven-day expense estimate and caveats.
The included artifact was trained on synthetic demonstration data and is not
validated for real-user financial decisions.
"""
from pathlib import Path
import re
import json
import numpy as np
import pandas as pd
import joblib

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = BASE_DIR / "models" / "cashflow_forecaster.joblib"

HORIZON_DAYS = 7
MIN_HISTORY_DAYS = 28
LIMITED_HISTORY_DAYS = 90
DAY_FIRST = False
REQUIRED_COLUMNS = ["date", "amount", "type"]
OPTIONAL_COLUMNS = ["user_id", "name", "category", "account", "note"]
EXPENSE_CATEGORIES = ["Food", "Transport", "Shopping", "Education", "Healthcare", "Bills", "Entertainment", "Other"]
BASELINES = {
    "Baseline: previous week total": lambda X: X["recent_week_expense"].to_numpy(),
    "Baseline: 28-day average x 7": lambda X: X["rolling_mean_28"].to_numpy() * HORIZON_DAYS,
}

def load_model_bundle(model_path=None):
    """Load the exact model bundle saved by the included notebook."""
    path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    return joblib.load(path)

TYPE_MAP = {
    "expense": "Expense", "expenses": "Expense", "debit": "Expense", "dr": "Expense", "spent": "Expense",
    "income": "Income", "credit": "Income", "cr": "Income", "deposit": "Income", "salary": "Income", "allowance": "Income",
    "transfer": "Transfer", "transfers": "Transfer",
}
CATEGORY_MAP = {
    "food": "Food", "food & dining": "Food", "dining": "Food", "groceries": "Food", "restaurant": "Food", "snacks": "Food",
    "transport": "Transport", "transportation": "Transport", "travel": "Transport", "commute": "Transport", "fuel": "Transport",
    "shopping": "Shopping", "clothing": "Shopping",
    "education": "Education", "books": "Education", "stationery": "Education", "tuition": "Education",
    "healthcare": "Healthcare", "health": "Healthcare", "medical": "Healthcare", "pharmacy": "Healthcare",
    "bills": "Bills", "utilities": "Bills", "recharge": "Bills", "subscription": "Bills", "subscriptions": "Bills",
    "entertainment": "Entertainment", "movies": "Entertainment", "games": "Entertainment",
    "other": "Other", "others": "Other", "misc": "Other", "miscellaneous": "Other",
}
# Spots credit-card BILL PAYMENTS (not purchases). Adjust the pattern for your own bank names.
CC_REPAYMENT_PATTERN = r"(?:credit|cc)\s*card.*(?:bill|payment|repay)|card\s*(?:bill|repayment)|\bcc\s*(?:bill|payment)"


def validate_schema(df):
    """Lower-case column names and make sure the required columns exist."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"The transaction data is missing required column(s): {missing}. "
            f"Columns found: {list(df.columns)}. Required: {REQUIRED_COLUMNS}. "
            f"Optional: {OPTIONAL_COLUMNS}."
        )
    return df


def clean_transactions(raw, verbose=True):
    """Clean raw transactions. Returns (clean_df, report)."""
    df = validate_schema(raw)
    report = {"rows_in_file": len(df)}

    has_user_id = "user_id" in df.columns
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    # 1) exact duplicates
    n_before = len(df)
    df = df.drop_duplicates()
    report["exact_duplicate_rows_removed"] = n_before - len(df)

    # 2) user_id
    if has_user_id:
        uid_text = df["user_id"].astype(str).str.strip()
        missing_uid = df["user_id"].isna() | uid_text.isin(["", "nan", "None", "<NA>"])
        report["rows_with_missing_user_id_removed"] = int(missing_uid.sum())
        df = df[~missing_uid].copy()
        df["user_id"] = uid_text[~missing_uid]
    else:
        df["user_id"] = "single_user"
        report["rows_with_missing_user_id_removed"] = 0

    # 3) dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=DAY_FIRST)
    if getattr(df["date"].dt, "tz", None) is not None:
        df["date"] = df["date"].dt.tz_localize(None)
    bad_date = df["date"].isna()
    report["rows_with_invalid_date_removed"] = int(bad_date.sum())
    df = df[~bad_date].copy()
    df["date"] = df["date"].dt.normalize()

    # 4) amounts
    if not pd.api.types.is_numeric_dtype(df["amount"]):
        df["amount"] = df["amount"].astype(str).str.replace(r"(?i)inr|rs\.?|[₹,\s]", "", regex=True)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    bad_amount = df["amount"].isna() | (df["amount"] == 0)
    report["rows_with_invalid_or_zero_amount_removed"] = int(bad_amount.sum())
    df = df[~bad_amount].copy()
    report["negative_amounts_made_positive"] = int((df["amount"] < 0).sum())
    df["amount"] = df["amount"].abs()

    # 5) type
    type_clean = df["type"].astype(str).str.strip().str.lower().map(TYPE_MAP)
    unknown_type = type_clean.isna()
    report["rows_with_unknown_type_removed"] = int(unknown_type.sum())
    if unknown_type.any() and verbose:
        print("Unknown 'type' labels dropped:", df.loc[unknown_type, "type"].astype(str).unique()[:5])
    df = df[~unknown_type].copy()
    df["type"] = type_clean[~unknown_type].astype(str)

    # 6) category
    raw_cat = df["category"].fillna("").astype(str).str.strip().str.lower()
    mapped_cat = raw_cat.map(CATEGORY_MAP)
    report["rows_with_missing_category_set_to_Other"] = int((raw_cat == "").sum())
    report["expense_rows_with_unrecognised_category_set_to_Other"] = int(((raw_cat != "") & mapped_cat.isna() & (df["type"] == "Expense")).sum())
    category_clean = mapped_cat.fillna("Other")

    # 7) credit-card bill payments (look at name + raw category text; used ONLY for exclusion)
    name_text = df["name"].fillna("").astype(str)
    text = (name_text + " " + df["category"].fillna("").astype(str)).str.lower()
    is_cc_payment = text.str.contains(CC_REPAYMENT_PATTERN, regex=True) & (df["type"] == "Expense")

    category_clean = category_clean.where(df["type"] != "Income", "Income")
    category_clean = category_clean.where(df["type"] != "Transfer", "Transfer")
    df["category"] = category_clean

    df["counts_as_expense"] = (df["type"] == "Expense") & ~is_cc_payment
    report["transfers_excluded_from_expenses"] = int((df["type"] == "Transfer").sum())
    report["credit_card_bill_payments_excluded"] = int(is_cc_payment.sum())

    df = df.sort_values(["user_id", "date"], kind="stable").reset_index(drop=True)
    report["rows_after_cleaning"] = len(df)

    if len(df) == 0:
        raise ValueError("No valid transactions remain after cleaning. Please check the dates, amounts and type columns.")
    if verbose:
        print(f"Cleaning done: {report['rows_in_file']:,} rows in -> {report['rows_after_cleaning']:,} rows kept.")
    return df[["user_id", "date", "name", "amount", "category", "account", "type", "note", "counts_as_expense"]], report

def make_daily_table(user_clean, end_date=None):
    """One user's cleaned transactions -> complete daily table (zeros for days with no expense)."""
    start = user_clean["date"].min()
    end = user_clean["date"].max() if end_date is None else pd.Timestamp(end_date)
    days = pd.date_range(start, end, freq="D")

    spend = user_clean[user_clean["counts_as_expense"]]
    income = user_clean[user_clean["type"] == "Income"]

    daily = pd.DataFrame(index=days)
    daily["expense"] = spend.groupby("date")["amount"].sum().reindex(days, fill_value=0.0)
    for cat in EXPENSE_CATEGORIES:
        daily[f"cat_{cat}"] = spend[spend["category"] == cat].groupby("date")["amount"].sum().reindex(days, fill_value=0.0)
    daily["income"] = income.groupby("date")["amount"].sum().reindex(days, fill_value=0.0)
    daily.index.name = "date"
    return daily

def build_features_for_user(daily):
    """Daily table of ONE user -> feature table (one row per forecast date).
    Every value in row t uses only days <= t."""
    f = pd.DataFrame(index=daily.index)
    e = daily["expense"]

    # lags: spending k days before the first forecast day (t+1)
    for k in (1, 7, 14, 28):
        f[f"expense_lag_{k}"] = e.shift(k - 1)

    # rolling averages / volatility over the last 7, 14, 28 days (including day t)
    for w in (7, 14, 28):
        f[f"rolling_mean_{w}"] = e.rolling(w, min_periods=w).mean()
    f["rolling_std_7"] = e.rolling(7, min_periods=7).std()
    f["rolling_std_28"] = e.rolling(28, min_periods=28).std()

    # weekly totals and changes
    f["recent_week_expense"] = e.rolling(7, min_periods=7).sum()
    f["previous_week_expense"] = f["recent_week_expense"].shift(7)
    f["week_over_week_change"] = f["recent_week_expense"] - f["previous_week_expense"]
    f["trend_7_vs_28"] = f["rolling_mean_7"] - f["rolling_mean_28"]

    # the user's own long-run level, using only the past
    f["user_avg_daily_expense_to_date"] = e.expanding(min_periods=28).mean()

    # category-wise recent spending
    for cat in EXPENSE_CATEGORIES:
        c = daily[f"cat_{cat}"]
        f[f"cat_{cat}_sum_7"] = c.rolling(7, min_periods=7).sum()
        f[f"cat_{cat}_sum_28"] = c.rolling(28, min_periods=28).sum()

    # income features
    f["income_sum_28"] = daily["income"].rolling(28, min_periods=28).sum()
    day_series = daily.index.to_series()
    last_income_day = day_series.where(daily["income"] > 0).ffill()
    f["days_since_income"] = (day_series - last_income_day).dt.days.fillna(60).clip(upper=60)

    # calendar facts about the first forecast day (t+1) - known in advance
    first_forecast_day = daily.index + pd.Timedelta(days=1)
    f["day_of_week"] = first_forecast_day.dayofweek
    f["day_of_month"] = first_forecast_day.day
    f["days_remaining_in_month"] = first_forecast_day.days_in_month - first_forecast_day.day
    f["window_has_month_start"] = np.any(
        [((daily.index + pd.Timedelta(days=i)).day == 1) for i in range(1, HORIZON_DAYS + 1)], axis=0
    ).astype(int)
    return f

def model_predict_from_features(bundle, features_row):
    """Use the bundle's model (or its baseline rule) to predict from a 1-row feature table."""
    if bundle["model"] is None:
        value = BASELINES[bundle["baseline_name"]](features_row)[0]
    else:
        value = bundle["model"].predict(features_row[bundle["feature_columns"]])[0]
    return float(max(value, 0.0))                           # spending cannot be negative


def make_observations(feat, min_amount=200):
    """Plain-language observations. A statement appears ONLY if the numbers support it."""
    obs = []
    recent, prev = feat["recent_week_expense"], feat["previous_week_expense"]
    if prev > 0 and abs(recent - prev) >= min_amount and abs(recent - prev) / prev >= 0.15:
        pct = (recent - prev) / prev * 100
        obs.append(f"Your latest week's expenses (₹{recent:,.0f}) were {abs(pct):.0f}% "
                   f"{'higher' if pct > 0 else 'lower'} than the week before (₹{prev:,.0f}).")
    m14, m28 = feat["rolling_mean_14"], feat["rolling_mean_28"]
    if m28 > 0 and abs(m14 - m28) / m28 >= 0.10 and abs(m14 - m28) * 7 >= min_amount:
        obs.append(f"Your recent 14-day average spending (₹{m14:,.0f}/day) is "
                   f"{'above' if m14 > m28 else 'below'} your 28-day average (₹{m28:,.0f}/day).")
    increases = []
    for cat in EXPENSE_CATEGORIES:
        last7 = feat[f"cat_{cat}_sum_7"]
        earlier_weekly = (feat[f"cat_{cat}_sum_28"] - last7) / 3          # average week in the 3 weeks before
        if earlier_weekly > 0 and last7 - earlier_weekly >= min_amount and last7 / earlier_weekly >= 1.25:
            increases.append((last7 - earlier_weekly, cat, last7, earlier_weekly))
    for _, cat, last7, earlier_weekly in sorted(increases, reverse=True)[:2]:
        obs.append(f"{cat} spending in the last 7 days (₹{last7:,.0f}) is higher than your own average for the "
                   f"3 weeks before (₹{earlier_weekly:,.0f} per week).")
    return obs


def predict_next_7_days(transactions, user_id, forecast_date=None, bundle=None):
    """Predict one user's total expenses for the 7 days AFTER forecast_date (default: user's last recorded day)."""
    if bundle is None:
        bundle = load_model_bundle()
    horizon = bundle["horizon_days"]
    result = {
        "user_id": str(user_id), "status": "no_data", "message": "", "forecast_date": None,
        "prediction_period": None, "predicted_expense_next_7_days": None, "typical_range": None,
        "recent_week_expense": None, "difference_from_recent_week_pct": None, "history_days": 0,
        "model_used": None, "month_to_date_expense": None, "estimated_rest_of_month_expense": None,
        "observations": [], "warnings": [],
    }

    # 1) select ONLY this user's transactions
    tx = transactions.copy()
    tx.columns = [str(c).strip().lower() for c in tx.columns]
    if "user_id" in tx.columns:
        tx = tx[tx["user_id"].astype(str).str.strip() == str(user_id)]
    elif str(user_id) != "single_user":
        result["message"] = "The data has no user_id column; use user_id='single_user'."
        return result
    if tx.empty:
        result["message"] = f"No transactions found for user '{user_id}'."
        return result

    # 2) same cleaning as in training
    try:
        clean_tx, _ = clean_transactions(tx, verbose=False)
    except ValueError as err:
        result["message"] = f"Could not use this user's data: {err}"
        return result

    # 3) only use information available by the forecast date
    fdate = clean_tx["date"].max() if forecast_date is None else pd.Timestamp(forecast_date).normalize()
    clean_tx = clean_tx[clean_tx["date"] <= fdate]
    if clean_tx.empty:
        result["status"] = "insufficient_data"
        result["message"] = "No transactions on or before the forecast date."
        return result
    daily = make_daily_table(clean_tx, end_date=fdate)
    n_days = len(daily)
    result["history_days"] = n_days
    result["forecast_date"] = str(fdate.date())
    start, end = fdate + pd.Timedelta(days=1), fdate + pd.Timedelta(days=horizon)
    result["prediction_period"] = f"{start:%d %b} – {end:%d %b %Y}"

    if bundle["training_data_type"] == "synthetic":
        result["warnings"].append("The model was trained on SYNTHETIC data: treat this as a demonstration, not as advice.")
    spent_days = daily.index[daily["expense"] > 0]
    days_quiet = (fdate - spent_days.max()).days if len(spent_days) else n_days
    if days_quiet > 14:
        result["warnings"].append(f"No expenses were recorded for {days_quiet} days. If you stopped logging, this forecast may be too low.")

    # 4) not enough history -> be honest
    if n_days < 7:
        result["status"] = "insufficient_data"
        result["message"] = (f"Only {n_days} day(s) of history. At least {bundle['min_history_days']} days are needed "
                             f"for a reliable personalised forecast, so no number is shown yet.")
        return result
    if n_days < bundle["min_history_days"]:
        rough = float(daily["expense"].mean() * horizon)
        result.update(status="baseline_only", predicted_expense_next_7_days=round(rough), model_used="simple average (low confidence)")
        result["message"] = (f"Only {n_days} days of history (reliable forecasts need {bundle['min_history_days']}+). "
                             f"This is just your average daily spending × 7, not a machine-learning forecast.")
        return result

    # 5) features -> prediction
    feats = build_features_for_user(daily).iloc[[-1]]
    if feats[bundle["feature_columns"]].isna().any(axis=None):
        result["status"] = "insufficient_data"
        result["message"] = "Some required features could not be computed from the available history."
        return result
    prediction = model_predict_from_features(bundle, feats)
    q = bundle["residual_quantiles"]
    row = feats.iloc[0]

    result.update(
        status="ok", model_used=bundle["model_name"],
        predicted_expense_next_7_days=round(prediction),
        typical_range=(round(max(0.0, prediction + q["q10"])), round(prediction + q["q90"])),
        recent_week_expense=round(float(row["recent_week_expense"])),
    )
    if row["recent_week_expense"] > 0:
        result["difference_from_recent_week_pct"] = round((prediction - row["recent_week_expense"]) / row["recent_week_expense"] * 100, 1)
    if n_days < bundle["limited_history_days"]:
        result["warnings"].append(f"Limited history ({n_days} days): the forecast is less reliable than for users with 3+ months of data.")

    # 6) rough month-end expense estimate (NOT a balance forecast)
    month_to_date = float(daily.loc[fdate.replace(day=1): fdate, "expense"].sum())
    days_left = fdate.days_in_month - fdate.day
    result["month_to_date_expense"] = round(month_to_date)
    result["estimated_rest_of_month_expense"] = round(prediction / horizon * days_left) if days_left > 0 else 0

    result["observations"] = make_observations(row)
    result["message"] = "Forecast based only on your own recent spending history."
    return result

def print_forecast_report(r):
    """Print a readable forecast report for terminal/manual testing."""
    print(f"User {r['user_id']} | status: {r['status']} | {r['message']}")
    if r.get("predicted_expense_next_7_days") is not None:
        print(f"Forecast period: {r['prediction_period']}")
        print(f"Predicted expenses: ₹{r['predicted_expense_next_7_days']:,}")
        if r.get("typical_range"):
            print(f"Illustrative range: ₹{r['typical_range'][0]:,}–₹{r['typical_range'][1]:,}")
    for item in r.get("observations", []):
        print("-", item)
    for warning in r.get("warnings", []):
        print("WARNING:", warning)
