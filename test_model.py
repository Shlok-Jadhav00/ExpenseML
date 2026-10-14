from ml.anomaly_model import analyze_expense

tests = [
    (100, "Food"),
    (300, "Food"),
    (1500, "Food"),
    (2000, "Shopping"),
    (100, "Transport"),
]

for amount, category in tests:
    result = analyze_expense(amount, category)
    print(f"₹{amount} {category} → {result}")