import { useState, useEffect } from "react";
import {
  Search,
  FlaskConical,
  TrendingUp,
  AlertTriangle,
  Info,
} from "lucide-react";
import { analyzeExpense, getForecast } from "../lib/api";
import { formatCurrency, formatDate } from "../lib/formatters";
import AnomalyBadge from "../components/ui/AnomalyBadge";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import ErrorBanner from "../components/ui/ErrorBanner";

const CATEGORIES = [
  "Food",
  "Shopping",
  "Transport",
  "Entertainment",
  "Education",
  "Bills",
  "Other",
];

export default function MLInsights() {
  /* ── Anomaly Analyzer state ── */
  const [analyzeForm, setAnalyzeForm] = useState({
    amount: "",
    category: "Food",
  });
  const [analyzeResult, setAnalyzeResult] = useState(null);
  const [analyzeError, setAnalyzeError] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  /* ── Forecast state ── */
  const [forecast, setForecast] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState(null);

  /* Load forecast on mount */
  useEffect(() => {
    loadForecast();
  }, []);

  async function loadForecast() {
    setForecastLoading(true);
    setForecastError(null);
    try {
      const data = await getForecast();
      setForecast(data);
    } catch (err) {
      setForecastError(err.message);
    } finally {
      setForecastLoading(false);
    }
  }

  async function handleAnalyze(e) {
    e.preventDefault();
    const amt = parseFloat(analyzeForm.amount);
    if (!analyzeForm.amount || isNaN(amt) || amt <= 0) return;

    setAnalyzing(true);
    setAnalyzeError(null);
    setAnalyzeResult(null);
    try {
      const data = await analyzeExpense(amt, analyzeForm.category);
      setAnalyzeResult(data);
    } catch (err) {
      setAnalyzeError(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  const inputBase =
    "w-full px-3 py-2.5 rounded-control bg-surface-secondary border border-border-subtle text-text-primary text-sm placeholder:text-text-secondary/60 focus:outline-none focus:ring-2 focus:ring-focus-ring transition-colors";

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">
          ML Insights & Sandbox
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Test the anomaly detection model and review spending forecasts.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ═══ Anomaly Analyzer ═══ */}
        <div className="rounded-card bg-surface border border-border-subtle shadow-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <FlaskConical size={18} className="text-action-primary" />
            <h2 className="text-sm font-semibold text-text-primary">
              Anomaly Analyzer
            </h2>
          </div>
          <p className="text-xs text-text-secondary mb-4">
            Test a hypothetical expense against the trained IsolationForest model
            without saving it to your records.
          </p>

          <form onSubmit={handleAnalyze} className="space-y-4">
            <div>
              <label
                htmlFor="analyze-amount"
                className="block text-xs font-medium text-text-secondary mb-1.5"
              >
                Amount (₹)
              </label>
              <input
                id="analyze-amount"
                type="number"
                value={analyzeForm.amount}
                onChange={(e) =>
                  setAnalyzeForm((p) => ({ ...p, amount: e.target.value }))
                }
                placeholder="e.g. 1500"
                min="0.01"
                step="0.01"
                className={`${inputBase} font-mono`}
              />
            </div>
            <div>
              <label
                htmlFor="analyze-category"
                className="block text-xs font-medium text-text-secondary mb-1.5"
              >
                Category
              </label>
              <select
                id="analyze-category"
                value={analyzeForm.category}
                onChange={(e) =>
                  setAnalyzeForm((p) => ({ ...p, category: e.target.value }))
                }
                className={inputBase}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={analyzing}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-control bg-action-primary text-background text-sm font-semibold hover:bg-action-primary/85 disabled:opacity-50 transition-all"
            >
              <Search size={15} />
              {analyzing ? "Analyzing…" : "Analyze Expense"}
            </button>
          </form>

          {/* Analyze result */}
          {analyzeError && (
            <div className="mt-4">
              <ErrorBanner message={analyzeError} />
            </div>
          )}
          {analyzeResult && (
            <div className="mt-5 p-4 rounded-control bg-surface-secondary border border-border-subtle space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-secondary font-medium uppercase tracking-wider">
                  Evaluation
                </span>
                <AnomalyBadge status={analyzeResult.status} />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-text-secondary">Anomaly Score</p>
                  <p className="text-sm font-mono font-semibold text-text-primary">
                    {analyzeResult.anomaly_score != null
                      ? analyzeResult.anomaly_score.toFixed(4)
                      : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-text-secondary">Category Avg</p>
                  <p className="text-sm font-mono font-semibold text-text-primary">
                    {analyzeResult.category_average != null
                      ? formatCurrency(analyzeResult.category_average)
                      : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-text-secondary">Z-Score</p>
                  <p className="text-sm font-mono font-semibold text-text-primary">
                    {analyzeResult.category_zscore != null
                      ? analyzeResult.category_zscore.toFixed(2)
                      : "—"}
                  </p>
                </div>
              </div>

              {analyzeResult.category_zscore != null &&
                analyzeResult.category_average != null && (
                  <p className="text-xs text-text-secondary leading-relaxed">
                    This amount is{" "}
                    <span className="font-mono font-medium text-text-primary">
                      {Math.abs(analyzeResult.category_zscore).toFixed(1)}
                    </span>{" "}
                    standard deviations from the{" "}
                    <span className="font-mono font-medium text-text-primary">
                      {formatCurrency(analyzeResult.category_average)}
                    </span>{" "}
                    average for {analyzeForm.category}.
                  </p>
                )}

              {analyzeResult.message && (
                <p className="text-xs text-text-secondary italic">
                  {analyzeResult.message}
                </p>
              )}
            </div>
          )}
        </div>

        {/* ═══ Spending Forecast ═══ */}
        <div className="rounded-card bg-surface border border-border-subtle shadow-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={18} className="text-accent-premium" />
            <h2 className="text-sm font-semibold text-text-primary">
              Spending Forecast
            </h2>
          </div>

          {forecastLoading ? (
            <LoadingSpinner variant="inline" />
          ) : forecastError ? (
            <ErrorBanner message={forecastError} onRetry={loadForecast} />
          ) : forecast ? (
            <div className="space-y-4">
              {forecast.status === "OK" ? (
                <>
                  <div className="p-4 rounded-control bg-surface-secondary border border-border-subtle text-center">
                    <p className="text-xs text-text-secondary mb-1">
                      Predicted spending for{" "}
                      {formatDate(forecast.prediction_date)}
                    </p>
                    <p className="text-3xl font-mono font-bold text-text-primary">
                      {formatCurrency(forecast.predicted_amount)}
                    </p>
                    <span className="inline-flex items-center gap-1 mt-2 px-2.5 py-0.5 rounded-badge text-xs font-medium bg-status-warning/15 text-status-warning">
                      <AlertTriangle size={11} />
                      Experimental
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-control bg-surface-secondary border border-border-subtle">
                      <p className="text-xs text-text-secondary">
                        Feature Date
                      </p>
                      <p className="text-sm font-mono text-text-primary">
                        {formatDate(forecast.feature_date)}
                      </p>
                    </div>
                    <div className="p-3 rounded-control bg-surface-secondary border border-border-subtle">
                      <p className="text-xs text-text-secondary">
                        Days of History
                      </p>
                      <p className="text-sm font-mono text-text-primary">
                        {forecast.days_of_history}
                      </p>
                    </div>
                  </div>
                </>
              ) : (
                <div className="p-4 rounded-control bg-surface-secondary border border-border-subtle">
                  <div className="flex items-start gap-3">
                    <Info
                      size={18}
                      className="text-status-warning mt-0.5 shrink-0"
                    />
                    <div>
                      <p className="text-sm font-medium text-text-primary">
                        {forecast.status}
                      </p>
                      <p className="text-xs text-text-secondary mt-1">
                        {forecast.message ||
                          "Not enough data to generate a forecast."}
                      </p>
                      {forecast.days_of_history != null && (
                        <div className="mt-3">
                          <div className="flex items-center justify-between text-xs text-text-secondary mb-1">
                            <span>Progress to forecast</span>
                            <span className="font-mono">
                              {forecast.days_of_history}/29 days
                            </span>
                          </div>
                          <div className="h-1.5 bg-background rounded-badge overflow-hidden">
                            <div
                              className="h-full bg-status-warning/60 rounded-badge transition-all"
                              style={{
                                width: `${Math.min(
                                  (forecast.days_of_history / 29) * 100,
                                  100
                                )}%`,
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Academic disclaimer */}
              <div className="flex items-start gap-2 p-3 rounded-control bg-background border border-border-subtle">
                <Info
                  size={14}
                  className="text-text-secondary mt-0.5 shrink-0"
                />
                <p className="text-xs text-text-secondary leading-relaxed">
                  Powered by IsolationForest &amp; Ridge Regression on
                  historical transactions. Trained on synthetic data — not
                  validated on real financial data. For academic demonstration
                  purposes only.
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
