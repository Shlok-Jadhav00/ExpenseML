# Expense Intelligence Project Verification Guide

Hi, I am sharing the current Expense Intelligence project.

Please follow these steps to verify it.

## 1. Extract the ZIP

Extract the project ZIP file and open PowerShell inside the extracted project folder.

## 2. Create and activate the virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

## 4. Start the FastAPI server

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Keep this terminal running.

## 5. Open the API documentation

Open this URL in a browser:

<http://127.0.0.1:8001/docs>

The Swagger page allows you to test the API endpoints.

## 6. Verify the endpoints

### `GET /health`

Click **Try it out**, then **Execute**.

Expected response:

```json
{
  "status": "healthy"
}
```

### `POST /analyze`

Click **Try it out** and use this request body:

```json
{
  "amount": 1500,
  "category": "Food"
}
```

Expected result: the response status should be `"Anomaly"`.

### `POST /transactions` for an expense

Use this request body:

```json
{
  "date": "2026-09-29",
  "name": "Swiggy",
  "amount": 1500,
  "category": "Food",
  "account": "Savings",
  "type": "expense",
  "note": "Dinner"
}
```

Expected result:

- HTTP status `201`
- `anomaly_status` should be `"Anomaly"`

### `POST /transactions` for income

Use this request body:

```json
{
  "date": "2026-09-29",
  "name": "Salary",
  "amount": 2500,
  "category": "Income",
  "account": "Savings",
  "type": "income",
  "note": "Monthly pay"
}
```

Expected result:

- HTTP status `201`
- `anomaly_status` should be `"Not Applicable"`

### Other transaction endpoints

Also verify these endpoints:

- `GET /transactions` lists stored transactions.
- `GET /transactions/{id}` retrieves one transaction.
- `DELETE /transactions/{id}` deletes a transaction.

## Important files

The project uses the existing trained anomaly model and SQLite database. Do not delete or modify these files:

```text
ml/anomaly_model.pkl
ml/category_stats.pkl
```

Please report whether the API starts successfully and whether the endpoints return the expected results.
