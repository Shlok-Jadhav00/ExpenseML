/**
 * Centralized API client for the ExpenseML backend.
 *
 * Every backend call flows through this module so that base URL
 * configuration, error handling, and response parsing happen in
 * exactly one place.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

/**
 * Generic fetch wrapper with consistent error handling.
 * Throws an Error with a user-readable message on failure.
 */
async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  let response;

  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options,
    });
  } catch (networkError) {
    throw new Error(
      "Unable to reach the backend server. Please ensure it is running on " +
        BASE_URL
    );
  }

  if (response.status === 204) return null;

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) {
        detail =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
      }
    } catch {
      /* response had no JSON body */
    }
    throw new Error(detail);
  }

  return response.json();
}

/* ── Transactions ── */

export async function fetchTransactions({
  category,
  type,
  account,
  limit,
  offset,
} = {}) {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (type) params.set("type", type);
  if (account) params.set("account", account);
  if (limit != null) params.set("limit", String(limit));
  if (offset != null) params.set("offset", String(offset));

  const qs = params.toString();
  return request(`/transactions${qs ? `?${qs}` : ""}`);
}

export async function createTransaction(data) {
  return request("/transactions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteTransaction(id) {
  return request(`/transactions/${id}`, { method: "DELETE" });
}

/* ── ML Analysis ── */

export async function analyzeExpense(amount, category) {
  return request("/analyze", {
    method: "POST",
    body: JSON.stringify({ amount, category }),
  });
}

/* ── Forecast ── */

export async function getForecast(date) {
  const qs = date ? `?date=${date}` : "";
  return request(`/forecast${qs}`);
}

/* ── Health ── */

export async function checkHealth() {
  return request("/health");
}
