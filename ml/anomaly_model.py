import joblib
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

model = joblib.load(BASE_DIR / "anomaly_model.pkl")
category_stats = joblib.load(BASE_DIR / "category_stats.pkl")

PERSONAL_HISTORY_MINIMUM = 10
PERSONAL_MODIFIED_Z_THRESHOLD = 3.5
MODIFIED_Z_CONSTANT = 0.6745


def analyze_expense(amount, category):
    if category not in category_stats.index:
        return {
            "status": "Unknown",
            "message": f"No training data available for category: {category}"
        }

    stats = category_stats.loc[category]

    category_zscore = (
        amount - stats["category_mean"]
    ) / stats["category_std"]

    features = pd.DataFrame(
        [[amount, category_zscore]],
        columns=["amount", "category_zscore"]
    )

    prediction = model.predict(features)[0]
    score = model.decision_function(features)[0]

    return {
        "status": "Anomaly" if prediction == -1 else "Normal",
        "anomaly_score": float(score),
        "category_average": float(stats["category_mean"]),
        "category_zscore": float(category_zscore)
    }


def _global_fallback(amount, category, explanation):
    """Run the fixed training-data baseline with an explicit explanation."""
    result = analyze_expense(amount, category)
    existing_message = result.get("message")
    result["scoring_method"] = "global_isolation_forest"
    result["message"] = " ".join(
        part
        for part in (
            explanation,
            "scoring_method=global_isolation_forest; anomaly_score is the "
            "Isolation Forest decision_function score and category_zscore is "
            "the global training-data Z-score.",
            existing_message,
        )
        if part
    )
    return result


def _usable_history(historical_amounts: Iterable[float]) -> list[float]:
    """Keep only finite, positive numeric historical expense amounts."""
    usable = []
    for value in historical_amounts if historical_amounts is not None else ():
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric_value) and numeric_value > 0:
            usable.append(numeric_value)
    return usable


def analyze_expense_with_history(
    amount,
    category,
    historical_amounts,
    *,
    minimum_history=PERSONAL_HISTORY_MINIMUM,
    modified_z_threshold=PERSONAL_MODIFIED_Z_THRESHOLD,
):
    """Analyze an expense against its category's personal history.

    The returned ``category_zscore`` is a personalized modified Z-score when
    enough variable history exists. In that path, ``anomaly_score`` is a
    decision margin: positive means within the threshold and negative means
    beyond it. The global Isolation Forest score is returned for fallbacks.
    """
    try:
        numeric_amount = float(amount)
    except (TypeError, ValueError):
        return {
            "status": "Unknown",
            "anomaly_score": None,
            "category_average": None,
            "category_zscore": None,
            "scoring_method": "none",
            "message": "Invalid expense amount; expected a finite positive number.",
        }

    if not math.isfinite(numeric_amount) or numeric_amount <= 0:
        return {
            "status": "Unknown",
            "anomaly_score": None,
            "category_average": None,
            "category_zscore": None,
            "scoring_method": "none",
            "message": "Invalid expense amount; expected a finite positive number.",
        }

    usable_history = _usable_history(historical_amounts)
    if len(usable_history) < minimum_history:
        return _global_fallback(
            numeric_amount,
            category,
            (
                f"Global baseline used provisionally: {len(usable_history)} usable "
                f"personal {category!r} expense(s) found; {minimum_history} required."
            ),
        )

    history = np.asarray(usable_history, dtype=float)
    personal_average = float(np.mean(history))
    median = float(np.median(history))
    mad = float(np.median(np.abs(history - median)))
    scale_method = "MAD"
    scale = mad

    if scale == 0 and np.ptp(history) > 0:
        first_quartile, third_quartile = np.percentile(history, [25, 75])
        iqr = float(third_quartile - first_quartile)
        if iqr > 0:
            scale = iqr / 1.349
            scale_method = "IQR-derived scale"
        else:
            standard_deviation = float(np.std(history, ddof=1))
            if standard_deviation > 0 and math.isfinite(standard_deviation):
                scale = standard_deviation
                scale_method = "standard-deviation fallback scale"

    if scale <= 0 or not math.isfinite(scale):
        return _global_fallback(
            numeric_amount,
            category,
            (
                "Global baseline used: personal history has no usable variation "
                "for a stable personalized scale."
            ),
        )

    modified_z = MODIFIED_Z_CONSTANT * (numeric_amount - median) / scale
    absolute_modified_z = abs(modified_z)
    decision_margin = modified_z_threshold - absolute_modified_z
    status = "Anomaly" if absolute_modified_z > modified_z_threshold else "Normal"

    return {
        "status": status,
        "anomaly_score": float(decision_margin),
        "category_average": personal_average,
        "category_zscore": float(modified_z),
        "scoring_method": "personal_modified_zscore",
        "message": (
            f"Personal baseline used with {scale_method}; "
            "scoring_method=personal_modified_zscore; category_zscore is a "
            "personalized modified Z-score, and anomaly_score is the "
            "modified-Z threshold margin."
        ),
    }


if __name__ == "__main__":
    print(analyze_expense(1500, "Food"))
    print(analyze_expense(200, "Food"))