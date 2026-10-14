/**
 * Formatting helpers used across pages and components.
 *
 * Centralizes currency, date, and number formatting so that
 * display rules live in exactly one place.
 */

/**
 * Format a number as Indian Rupee currency.
 * Example: 14320 → "₹14,320"
 */
export function formatCurrency(amount) {
  if (amount == null || isNaN(amount)) return "₹0";
  return `₹${Number(amount).toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Format a date string or Date object to a readable locale format.
 * Example: "2026-10-12" → "12 Oct 2026"
 */
export function formatDate(dateValue) {
  if (!dateValue) return "";
  const d = typeof dateValue === "string" ? new Date(dateValue) : dateValue;
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/**
 * Format a date string to just day and month.
 * Example: "2026-10-12" → "12 Oct"
 */
export function formatShortDate(dateValue) {
  if (!dateValue) return "";
  const d = typeof dateValue === "string" ? new Date(dateValue) : dateValue;
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

/**
 * Get a greeting based on the current time of day.
 */
export function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good Morning";
  if (hour < 17) return "Good Afternoon";
  return "Good Evening";
}

/**
 * Get today's date formatted nicely.
 */
export function getTodayFormatted() {
  return formatDate(new Date());
}

/**
 * Get today in YYYY-MM-DD format for date inputs.
 */
export function getTodayISO() {
  return new Date().toISOString().split("T")[0];
}
