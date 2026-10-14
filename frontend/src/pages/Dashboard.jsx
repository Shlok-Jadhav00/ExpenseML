import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Wallet,
  CalendarRange,
  ShieldAlert,
  TrendingUp,
  ArrowRight,
} from "lucide-react";
import { fetchTransactions, getForecast } from "../lib/api";
import { formatCurrency, formatDate } from "../lib/formatters";
import MetricCard from "../components/ui/MetricCard";
import AnomalyBadge from "../components/ui/AnomalyBadge";
import CategoryPill from "../components/ui/CategoryPill";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import CategoryDonut from "../components/charts/CategoryDonut";
import SpendingTrend from "../components/charts/SpendingTrend";

export default function Dashboard() {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [txData, fcData] = await Promise.all([
        fetchTransactions({ limit: 500 }),
        getForecast().catch(() => null),
      ]);
      setTransactions(txData.transactions);
      setTotalCount(txData.count);
      setForecast(fcData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  /* ── Computed metrics from real data ── */
  const metrics = useMemo(() => {
    const expenses = transactions.filter((t) => t.type === "expense");
    const totalExpenses = expenses.reduce((sum, t) => sum + t.amount, 0);

    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();
    const monthlyExpenses = expenses
      .filter((t) => {
        const d = new Date(t.date);
        return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
      })
      .reduce((sum, t) => sum + t.amount, 0);

    const anomalies = transactions.filter(
      (t) => t.anomaly_status === "Anomaly"
    );

    /* Category breakdown for donut chart */
    const categoryMap = {};
    expenses.forEach((t) => {
      categoryMap[t.category] = (categoryMap[t.category] || 0) + t.amount;
    });
    const categoryData = Object.entries(categoryMap)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);

    /* Daily aggregates for spending trend (last 30 days) */
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const dailyMap = {};
    expenses
      .filter((t) => new Date(t.date) >= thirtyDaysAgo)
      .forEach((t) => {
        dailyMap[t.date] = (dailyMap[t.date] || 0) + t.amount;
      });
    const trendData = Object.entries(dailyMap)
      .map(([date, amount]) => ({ date, amount }))
      .sort((a, b) => a.date.localeCompare(b.date));

    return {
      totalExpenses,
      monthlyExpenses,
      anomalies,
      anomalyCount: anomalies.length,
      categoryData,
      trendData,
      recent: transactions.slice(0, 5),
    };
  }, [transactions]);

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className="space-y-6">
        <LoadingSpinner variant="cards" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="animate-skeleton h-72 rounded-card" />
          <div className="animate-skeleton h-72 rounded-card" />
        </div>
      </div>
    );
  }

  /* ── Error state ── */
  if (error) {
    return <ErrorBanner message={error} onRetry={loadData} />;
  }

  /* ── Empty state ── */
  if (transactions.length === 0) {
    return (
      <EmptyState
        title="No transactions recorded yet"
        message="Add your first expense to unlock AI-powered insights, anomaly detection, and spending forecasts."
        actionLabel="Add Your First Expense"
        onAction={() => navigate("/add")}
      />
    );
  }

  /* ── Forecast card badge ── */
  const forecastBadge =
    forecast && forecast.status === "OK"
      ? {
          label: "Experimental",
          className: "bg-status-warning/15 text-status-warning",
        }
      : {
          label: forecast?.status === "Insufficient Data" ? "Awaiting Data" : "Unavailable",
          className: "bg-surface-secondary text-text-secondary",
        };

  return (
    <div className="space-y-6">
      {/* ── Metric Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Expenses"
          value={formatCurrency(metrics.totalExpenses)}
          icon={Wallet}
          subtitle={`${totalCount} transaction${totalCount !== 1 ? "s" : ""} recorded`}
        />
        <MetricCard
          title="This Month"
          value={formatCurrency(metrics.monthlyExpenses)}
          icon={CalendarRange}
          subtitle="Current month spending"
        />
        <MetricCard
          title="Anomalies Flagged"
          value={String(metrics.anomalyCount)}
          icon={ShieldAlert}
          subtitle={
            metrics.anomalyCount > 0
              ? "Unusual spending detected"
              : "Great spending discipline!"
          }
        />
        <MetricCard
          title="Tomorrow's Forecast"
          value={
            forecast && forecast.status === "OK"
              ? formatCurrency(forecast.predicted_amount)
              : "—"
          }
          icon={TrendingUp}
          badge={forecastBadge}
          subtitle={
            forecast && forecast.status === "Insufficient Data"
              ? forecast.message
              : forecast && forecast.status === "OK"
                ? `Based on ${forecast.days_of_history} days of history`
                : null
          }
        />
      </div>

      {/* ── Charts + Recent ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown */}
        <div className="rounded-card bg-surface border border-border-subtle shadow-card p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-4">
            Category Breakdown
          </h2>
          {metrics.categoryData.length > 0 ? (
            <CategoryDonut data={metrics.categoryData} />
          ) : (
            <p className="text-sm text-text-secondary py-8 text-center">
              No expense data to display
            </p>
          )}
        </div>

        {/* Recent Transactions */}
        <div className="rounded-card bg-surface border border-border-subtle shadow-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text-primary">
              Recent Transactions
            </h2>
            <button
              onClick={() => navigate("/history")}
              className="text-xs text-action-primary hover:text-action-primary/80 font-medium inline-flex items-center gap-1 transition-colors"
            >
              View All <ArrowRight size={12} />
            </button>
          </div>
          <div className="space-y-3">
            {metrics.recent.map((tx) => (
              <div
                key={tx.id}
                className="flex items-center justify-between py-2 border-b border-border-subtle last:border-0"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <CategoryPill category={tx.category} />
                  <div className="min-w-0">
                    <p className="text-sm text-text-primary truncate">
                      {tx.name}
                    </p>
                    <p className="text-xs text-text-secondary">
                      {formatDate(tx.date)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-sm font-mono font-semibold text-text-primary">
                    {formatCurrency(tx.amount)}
                  </span>
                  <AnomalyBadge status={tx.anomaly_status} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Spending Trend + Anomaly Highlights ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Spending Trend */}
        <div className="rounded-card bg-surface border border-border-subtle shadow-card p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-4">
            Spending Trend (30 Days)
          </h2>
          {metrics.trendData.length > 0 ? (
            <SpendingTrend data={metrics.trendData} />
          ) : (
            <p className="text-sm text-text-secondary py-8 text-center">
              Not enough data for trend analysis
            </p>
          )}
        </div>

        {/* Anomaly Highlights */}
        <div className="rounded-card bg-surface border border-border-subtle shadow-card p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-4">
            Anomaly Highlights
          </h2>
          {metrics.anomalies.length > 0 ? (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {metrics.anomalies.map((tx) => (
                <div
                  key={tx.id}
                  className="flex items-center justify-between py-2 px-3 rounded-control bg-status-anomaly/5 border border-status-anomaly/10"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-text-primary truncate">
                      {tx.name}
                    </p>
                    <p className="text-xs text-text-secondary">
                      {tx.category} · {formatDate(tx.date)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-sm font-mono font-semibold text-status-anomaly">
                      {formatCurrency(tx.amount)}
                    </span>
                    {tx.anomaly_score != null && (
                      <span className="text-xs font-mono text-text-secondary">
                        Score: {tx.anomaly_score.toFixed(3)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center">
              <p className="text-sm text-text-secondary">
                No anomalous expenses detected. Great spending discipline!
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
