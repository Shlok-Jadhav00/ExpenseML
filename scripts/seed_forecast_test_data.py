"""Seed and clean up temporary synthetic data for forecast API testing."""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import SessionLocal
from backend.models import Transaction


TEST_MARKER = "[TEMP_FORECAST_TEST_20261012]"
START_DATE = date(2026, 9, 14)
END_DATE = date(2026, 10, 12)
ACCOUNT = "Forecast Test Account"

CATEGORY_RANGES = {
    "Food": (120, 650),
    "Transport": (40, 320),
    "Shopping": (250, 1800),
    "Entertainment": (150, 900),
    "Education": (100, 750),
    "Bills": (300, 1400),
}
MERCHANTS = {
    "Food": ("Canteen", "Cafe", "Restaurant"),
    "Transport": ("Bus", "Metro", "Auto"),
    "Shopping": ("Supermarket", "Clothing Store", "Online Store"),
    "Entertainment": ("Movie", "Streaming", "Game"),
    "Education": ("Books", "Stationery", "Course Material"),
    "Bills": ("Mobile Bill", "Internet", "Recharge"),
}


def expected_dates() -> list[date]:
    """Return every inclusive date in the temporary test period."""
    days = (END_DATE - START_DATE).days + 1
    return [START_DATE + timedelta(days=offset) for offset in range(days)]


def build_test_records() -> list[Transaction]:
    """Build deterministic, varied expense records for each expected date."""
    generator = random.Random(20261012)
    categories = list(CATEGORY_RANGES)
    records = []

    for offset, transaction_date in enumerate(expected_dates()):
        category = categories[offset % len(categories)]
        minimum, maximum = CATEGORY_RANGES[category]
        amount = generator.randint(minimum, maximum)
        if transaction_date.weekday() >= 5 and category == "Food":
            amount += 100

        merchant = generator.choice(MERCHANTS[category])
        records.append(
            Transaction(
                date=transaction_date,
                name=f"Temporary Forecast Test - {merchant}",
                amount=float(amount),
                category=category,
                account=ACCOUNT,
                type="expense",
                note=f"{TEST_MARKER} Synthetic forecast test data",
                anomaly_status="Unknown",
                anomaly_score=None,
            )
        )

    return records


def marked_records(db) -> list[Transaction]:
    """Return only records created by this script's unique marker."""
    return (
        db.query(Transaction)
        .filter(Transaction.note.contains(TEST_MARKER))
        .order_by(Transaction.date, Transaction.id)
        .all()
    )


def print_status(existing_dates: set[date]) -> None:
    """Print the status of each expected date without changing the database."""
    print(f"Temporary marker: {TEST_MARKER}")
    print(f"Expected date range: {START_DATE} through {END_DATE}")
    print(f"Expected dates: {len(expected_dates())}")
    print(f"Marked dates present: {len(existing_dates)}")
    missing = [day for day in expected_dates() if day not in existing_dates]
    print(f"Missing dates: {len(missing)}")
    if missing:
        print("Missing date values:")
        for missing_date in missing:
            print(f"  {missing_date}")


def seed() -> None:
    """Insert only missing marked dates in one transaction."""
    records = build_test_records()
    expected = set(expected_dates())

    with SessionLocal.begin() as db:
        existing = marked_records(db)
        existing_dates = {record.date for record in existing}
        print_status(existing_dates)

        if expected.issubset(existing_dates):
            print("All expected temporary records already exist; nothing inserted.")
            return

        missing_dates = expected - existing_dates
        missing_records = [record for record in records if record.date in missing_dates]
        db.add_all(missing_records)
        print(f"Inserted {len(missing_records)} missing temporary records.")


def list_records() -> None:
    """Preview marked records without changing the database."""
    with SessionLocal() as db:
        records = marked_records(db)
        print_status({record.date for record in records})
        for record in records:
            print(
                f"{record.date} | {record.category:<13} | "
                f"{record.amount:>7.2f} | {record.name}"
            )


def cleanup() -> None:
    """Delete only records containing this script's unique marker."""
    with SessionLocal.begin() as db:
        records = marked_records(db)
        deleted_count = len(records)
        for record in records:
            db.delete(record)
        print(f"Deleted {deleted_count} temporary forecast test records.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage temporary synthetic forecast test transactions."
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--list",
        action="store_true",
        help="Preview marked records and missing expected dates.",
    )
    actions.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete only records with this script's unique marker.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_args()
    if arguments.list:
        list_records()
    elif arguments.cleanup:
        cleanup()
    else:
        seed()


if __name__ == "__main__":
    main()