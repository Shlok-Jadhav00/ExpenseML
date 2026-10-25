/**
 * Centralized API client for the ExpenseML backend.
 *
 * Every backend call flows through this module so that base URL
 * configuration, error handling, cookie credentials, and CSRF
 * tokens are managed in exactly one place.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

/** Cached CSRF token — refreshed after login / register. */
let _csrfToken = null;

/**
 * Generic fetch wrapper with consistent error handling.
 * Throws an Error with a user-readable message on failure.
 * All requests include credentials so the session cookie is sent.
 */
async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const { headers: optionHeaders, ...restOptions } = options;
  let response;

  try {
    response = await fetch(url, {
      credentials: "include",
      ...restOptions,
      headers: { "Content-Type": "application/json", ...optionHeaders },
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

    const err = new Error(detail);
    err.status = response.status;
    throw err;
  }

  return response.json();
}

/**
 * Perform a state-changing request that requires the X-CSRF-Token header.
 * Automatically attaches the cached CSRF token.
 */
async function mutationRequest(path, options = {}) {
  const csrfToken = await getCsrfToken();
  return request(path, {
    ...options,
    headers: {
      ...options.headers,
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
  });
}

/* ── Auth ── */

export async function authRegister(email, password) {
  const data = await request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  _csrfToken = null; // Force refresh after new session
  return data;
}

export async function authLogin(email, password) {
  const data = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  _csrfToken = null; // Force refresh after new session
  return data;
}

export async function authMe() {
  return request("/auth/me");
}

export async function authLogout() {
  const result = await mutationRequest("/auth/logout", { method: "POST" });
  _csrfToken = null;
  return result;
}

export async function authDeleteAccount(password) {
  const result = await mutationRequest("/auth/account", {
    method: "DELETE",
    body: JSON.stringify({ password }),
  });
  _csrfToken = null;
  return result;
}

/* ── CSRF ── */

export async function fetchCsrfToken() {
  const data = await request("/auth/csrf");
  _csrfToken = data.token;
  return _csrfToken;
}

export async function getCsrfToken() {
  if (_csrfToken) return _csrfToken;
  try {
    return await fetchCsrfToken();
  } catch {
    return null;
  }
}

export function clearCsrfToken() {
  _csrfToken = null;
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
  return mutationRequest("/transactions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteTransaction(id) {
  return mutationRequest(`/transactions/${id}`, { method: "DELETE" });
}

/* ── ML Analysis ── */

export async function analyzeExpense(amount, category) {
  return mutationRequest("/analyze", {
    method: "POST",
    body: JSON.stringify({ amount, category }),
  });
}

/* ── Forecast ── */

export async function getForecast(date) {
  const qs = date ? `?date=${date}` : "";
  return request(`/forecast${qs}`);
}

export async function getCashflowForecast(date) {
  const qs = date ? `?date=${date}` : "";
  return request(`/cashflow-forecast${qs}`);
}

/* ── Health ── */

export async function checkHealth() {
  return request("/health");
}
