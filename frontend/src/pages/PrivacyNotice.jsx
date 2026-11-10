import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";

export default function PrivacyNotice() {
  const { acknowledgePrivacyNotice } = useAuth();
  const navigate = useNavigate();
  const [research, setResearch] = useState(false);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await acknowledgePrivacyNotice({
        privacy_notice_version: "2026-11-beta-1",
        privacy_notice_accepted: true,
        research_consent: research,
        research_consent_version: research ? "2026-11-beta-1" : null,
      });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <form onSubmit={submit} className="w-full max-w-xl rounded-card bg-surface border border-border-subtle shadow-card p-6 space-y-5">
        <h1 className="text-xl font-semibold text-text-primary">ExpenseML beta notice</h1>
        <p className="text-sm text-text-secondary leading-relaxed">
          ExpenseML is an experimental beta application. You manually enter transactions,
          which are stored in the hosted database to provide your account history, forecasts,
          and anomaly analysis. Predictions may be incorrect and are not financial advice.
          You can request account and transaction deletion from the Account page.
        </p>
        <p className="text-sm text-text-secondary leading-relaxed">
          We collect your email for authentication and the transaction fields you submit to
          provide the application features. Optional research data is used only for controlled
          aggregate evaluation when you consent; it is not automatically used to retrain models.
        </p>
        {error && <p className="text-sm text-status-anomaly">{error}</p>}
        <label className="flex items-start gap-2 text-sm text-text-secondary">
          <input type="checkbox" required className="mt-1" />
          <span>I acknowledge this beta privacy notice.</span>
        </label>
        <label className="flex items-start gap-2 text-sm text-text-secondary">
          <input type="checkbox" checked={research} onChange={(e) => setResearch(e.target.checked)} className="mt-1" />
          <span>Optional: consent to controlled aggregate ML evaluation and research. This can be withdrawn later.</span>
        </label>
        <button type="submit" disabled={submitting} className="w-full px-4 py-3 rounded-control bg-action-primary text-background font-semibold disabled:opacity-50">
          {submitting ? "Saving…" : "Continue"}
        </button>
      </form>
    </div>
  );
}
