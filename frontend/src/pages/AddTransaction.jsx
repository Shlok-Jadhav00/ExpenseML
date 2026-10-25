import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Send } from "lucide-react";
import { createTransaction } from "../lib/api";
import { getTodayISO } from "../lib/formatters";
import AnomalyBadge from "../components/ui/AnomalyBadge";
import Toast from "../components/ui/Toast";

const CATEGORIES = [
  "Food",
  "Shopping",
  "Transport",
  "Entertainment",
  "Education",
  "Bills",
  "Other",
];
const INCOME_CATEGORIES = ["Allowance", "Salary", "Petty Cash", "Bonus", "Other"];
const ACCOUNTS = ["Savings", "Cash", "UPI", "Credit Card"];
const TYPES = ["expense", "income", "transfer"];

const INITIAL_FORM = {
  date: getTodayISO(),
  name: "",
  amount: "",
  category: "Food",
  account: "Savings",
  to_account: "Cash",
  type: "expense",
  note: "",
};

export default function AddTransaction() {
  const navigate = useNavigate();
  const [form, setForm] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState(null);
  const [result, setResult] = useState(null);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => {
      if (name === "type") {
        return {
          ...prev,
          type: value,
          category: value === "expense" ? "Food" : value === "income" ? "Allowance" : "",
          to_account: value === "transfer" ? (prev.account === "Cash" ? "Savings" : "Cash") : "",
        };
      }
      return { ...prev, [name]: value };
    });
    if (name === "type") {
      setErrors((prev) => {
        const next = { ...prev };
        delete next.category;
        delete next.to_account;
        return next;
      });
    } else if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  }

  function validate() {
    const errs = {};
    if (!form.date) errs.date = "Date is required";
    if (!form.name.trim()) errs.name = "Name is required";
    const amt = parseFloat(form.amount);
    if (!form.amount || isNaN(amt) || amt <= 0)
      errs.amount = "Amount must be greater than 0";
    if (form.type !== "transfer" && !form.category) errs.category = "Category is required";
    if (!form.account) errs.account = "Account is required";
    if (form.type === "transfer") {
      if (!form.to_account) errs.to_account = "To Account is required";
      if (form.account && form.account === form.to_account) {
        errs.to_account = "From and To accounts must be different";
      }
    }
    return errs;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        date: form.date,
        name: form.name.trim(),
        amount: parseFloat(form.amount),
        ...(form.type !== "transfer" ? { category: form.category } : {}),
        account: form.account,
        ...(form.type === "transfer" ? { to_account: form.to_account } : {}),
        type: form.type,
        note: form.note.trim() || null,
      };
      const data = await createTransaction(payload);
      setResult(data);
      setToast({
        type: "success",
        message:
          form.type === "transfer"
            ? "Transfer saved successfully"
            : form.type === "income"
              ? "Income saved successfully"
              : `Transaction saved — ${data.anomaly_status === "Anomaly" ? "flagged as anomaly" : "marked as normal"}`,
      });
      /* Redirect after a brief pause so the user sees the result */
      setTimeout(() => navigate("/"), 2000);
    } catch (err) {
      setToast({ type: "error", message: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  const inputBase =
    "w-full px-3 py-2.5 rounded-control bg-surface-secondary border border-border-subtle text-text-primary text-sm placeholder:text-text-secondary/60 focus:outline-none focus:ring-2 focus:ring-focus-ring transition-colors";
  const labelBase = "block text-xs font-medium text-text-secondary mb-1.5";
  const errorText = "text-xs text-status-anomaly mt-1";

  return (
    <div className="max-w-xl mx-auto">
      <div className="rounded-card bg-surface border border-border-subtle shadow-card p-6 md:p-8">
        <h1 className="text-lg font-semibold text-text-primary mb-1">
          Add Transaction
        </h1>
        <p className="text-sm text-text-secondary mb-6">
          Record a new expense, income, or transfer. Expenses are automatically
          analysed for anomalies.
        </p>

        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* Date + Name row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="tx-date" className={labelBase}>
                Date
              </label>
              <input
                id="tx-date"
                type="date"
                name="date"
                value={form.date}
                onChange={handleChange}
                className={inputBase}
              />
              {errors.date && <p className={errorText}>{errors.date}</p>}
            </div>
            <div>
              <label htmlFor="tx-name" className={labelBase}>
                Merchant / Payee
              </label>
              <input
                id="tx-name"
                type="text"
                name="name"
                value={form.name}
                onChange={handleChange}
                placeholder="e.g. Swiggy"
                className={inputBase}
              />
              {errors.name && <p className={errorText}>{errors.name}</p>}
            </div>
          </div>

          {/* Amount */}
          <div>
            <label htmlFor="tx-amount" className={labelBase}>
              Amount (₹)
            </label>
            <input
              id="tx-amount"
              type="number"
              name="amount"
              value={form.amount}
              onChange={handleChange}
              placeholder="0.00"
              min="0.01"
              step="0.01"
              className={`${inputBase} font-mono`}
            />
            {errors.amount && <p className={errorText}>{errors.amount}</p>}
          </div>

          {/* Category + Account row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {form.type !== "transfer" ? (
              <div>
                <label htmlFor="tx-category" className={labelBase}>
                  Category
                </label>
                <select
                  id="tx-category"
                  name="category"
                  value={form.category}
                  onChange={handleChange}
                  className={inputBase}
                >
                  {(form.type === "income" ? INCOME_CATEGORIES : CATEGORIES).map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                {errors.category && (
                  <p className={errorText}>{errors.category}</p>
                )}
              </div>
            ) : (
              <div className="flex items-center text-xs text-text-secondary">
                Transfers move money between accounts and are not analyzed as expenses.
              </div>
            )}
            <div>
              <label htmlFor="tx-account" className={labelBase}>
                {form.type === "transfer" ? "From Account" : "Account"}
              </label>
              <select
                id="tx-account"
                name="account"
                value={form.account}
                onChange={handleChange}
                className={inputBase}
              >
                {ACCOUNTS.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
              {errors.account && (
                <p className={errorText}>{errors.account}</p>
              )}
            </div>
          </div>

          {form.type === "transfer" && (
            <div>
              <label htmlFor="tx-to-account" className={labelBase}>
                To Account
              </label>
              <select
                id="tx-to-account"
                name="to_account"
                value={form.to_account}
                onChange={handleChange}
                className={inputBase}
              >
                {ACCOUNTS.map((account) => (
                  <option key={account} value={account}>
                    {account}
                  </option>
                ))}
              </select>
              {errors.to_account && (
                <p className={errorText}>{errors.to_account}</p>
              )}
            </div>
          )}

          {/* Type — radio group */}
          <fieldset>
            <legend className={`${labelBase} mb-2`}>Type</legend>
            <div className="flex gap-3">
              {TYPES.map((t) => (
                <label
                  key={t}
                  className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-control border text-sm font-medium cursor-pointer transition-all ${
                    form.type === t
                      ? "border-action-primary bg-action-primary/10 text-action-primary"
                      : "border-border-subtle text-text-secondary hover:border-text-secondary/30 hover:bg-surface-secondary"
                  }`}
                >
                  <input
                    type="radio"
                    name="type"
                    value={t}
                    checked={form.type === t}
                    onChange={handleChange}
                    className="sr-only"
                  />
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </label>
              ))}
            </div>
          </fieldset>

          {/* Note */}
          <div>
            <label htmlFor="tx-note" className={labelBase}>
              Note (optional)
            </label>
            <textarea
              id="tx-note"
              name="note"
              value={form.note}
              onChange={handleChange}
              rows={2}
              placeholder="Add a quick note…"
              className={`${inputBase} resize-none`}
            />
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-control bg-action-primary text-background font-semibold text-sm hover:bg-action-primary/85 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <Send size={16} strokeWidth={2} />
            {submitting ? "Saving…" : "Save Transaction"}
          </button>
        </form>

        {/* Immediate ML result */}
        {result && (
          <div className="mt-6 p-4 rounded-control bg-surface-secondary border border-border-subtle flex items-center justify-between">
            <div>
              <p className="text-sm text-text-primary font-medium">
                ML Evaluation Result
              </p>
              <p className="text-xs text-text-secondary mt-0.5">
                {result.anomaly_score != null
                  ? `Anomaly score: ${result.anomaly_score.toFixed(4)}`
                  : "No score available for this transaction type"}
              </p>
            </div>
            <AnomalyBadge status={result.anomaly_status} />
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
