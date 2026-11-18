import { useState, useEffect, useCallback, useMemo } from "react";
import { Trash2, Filter, Layers, PieChart as ChartIcon, X, Check } from "lucide-react";
import { fetchTransactions, deleteTransaction, fetchCategorySummary } from "../lib/api";
import { formatCurrency, formatDate } from "../lib/formatters";
import AnomalyBadge from "../components/ui/AnomalyBadge";
import CategoryPill from "../components/ui/CategoryPill";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import ConfirmModal from "../components/ui/ConfirmModal";
import Toast from "../components/ui/Toast";
import CategoryBreakdownChart from "../components/charts/CategoryBreakdownChart";
import { getCategoryColor } from "../lib/categoryColors";
import { useNavigate } from "react-router-dom";

const PAGE_SIZE = 20;
const ALL_CATEGORIES = [
  { id: "Food", label: "Food" },
  { id: "Transport", label: "Travel / Transport" },
  { id: "Shopping", label: "Shopping" },
  { id: "Entertainment", label: "Entertainment" },
  { id: "Education", label: "Education" },
  { id: "Bills", label: "Bills" },
  { id: "Other", label: "Other" },
];
const TYPES = ["", "expense", "income", "transfer"];

export default function TransactionHistory() {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [filterType, setFilterType] = useState("");
  const [showChart, setShowChart] = useState(true);

  // Category summary data
  const [categorySummary, setCategorySummary] = useState({
    total_expense: 0,
    categories: [],
  });

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [toast, setToast] = useState(null);

  // Fetch category summary stats
  const loadCategorySummary = useCallback(async () => {
    try {
      const summary = await fetchCategorySummary();
      if (summary && Array.isArray(summary.categories)) {
        setCategorySummary(summary);
      }
    } catch {
      // Fallback: gracefully ignore if server doesn't respond
    }
  }, []);

  const loadData = useCallback(
    async (reset = false) => {
      const isReset = reset || offset === 0;
      if (isReset) {
        setLoading(true);
      } else {
        setLoadingMore(true);
      }
      setError(null);

      try {
        const currentOffset = isReset ? 0 : offset;
        const data = await fetchTransactions({
          categories: selectedCategories.length > 0 ? selectedCategories : undefined,
          type: filterType || undefined,
          limit: PAGE_SIZE,
          offset: currentOffset,
        });

        if (isReset) {
          setTransactions(data.transactions);
          setOffset(PAGE_SIZE);
        } else {
          setTransactions((prev) => [...prev, ...data.transactions]);
          setOffset((prev) => prev + PAGE_SIZE);
        }
        setTotalCount(data.count);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [offset, selectedCategories, filterType]
  );

  // Initial load
  useEffect(() => {
    loadCategorySummary();
  }, [loadCategorySummary]);

  // Reload table on filter change
  useEffect(() => {
    setOffset(0);
    setTransactions([]);
    loadData(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCategories, filterType]);

  // Category toggle handler
  function toggleCategory(cat) {
    setSelectedCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  }

  function clearCategorySelection() {
    setSelectedCategories([]);
  }

  // Combined statistics for selected categories
  const combinedStats = useMemo(() => {
    if (selectedCategories.length === 0) {
      return null;
    }
    const matchingItems = categorySummary.categories.filter((c) =>
      selectedCategories.includes(c.name)
    );
    const combinedAmount = matchingItems.reduce((sum, c) => sum + c.value, 0);
    const combinedItemCount = matchingItems.reduce((sum, c) => sum + c.count, 0);
    const combinedPct =
      categorySummary.total_expense > 0
        ? ((combinedAmount / categorySummary.total_expense) * 100).toFixed(1)
        : 0;

    return {
      amount: combinedAmount,
      percentage: combinedPct,
      count: combinedItemCount,
    };
  }, [selectedCategories, categorySummary]);

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteTransaction(deleteTarget.id);
      setTransactions((prev) => prev.filter((t) => t.id !== deleteTarget.id));
      setTotalCount((prev) => prev - 1);
      loadCategorySummary(); // refresh categories after deletion
      setToast({
        type: "success",
        message: `"${deleteTarget.name}" deleted successfully`,
      });
    } catch (err) {
      setToast({ type: "error", message: err.message });
    } finally {
      setDeleteTarget(null);
    }
  }

  const hasMore = transactions.length < totalCount;
  const selectBase =
    "px-3 py-1.5 rounded-control bg-surface-secondary border border-border-subtle text-text-primary text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-focus-ring";

  if (loading && offset === 0 && transactions.length === 0) {
    return (
      <div className="space-y-4">
        <div className="animate-skeleton h-10 w-64 rounded-control" />
        <LoadingSpinner variant="table" />
      </div>
    );
  }

  if (error && transactions.length === 0) {
    return <ErrorBanner message={error} onRetry={() => loadData(true)} />;
  }

  return (
    <div className="space-y-5">
      {/* ── Page Header & Controls ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">
            Transaction History
          </h1>
          <p className="text-xs text-text-secondary mt-0.5">
            {totalCount} transaction{totalCount !== 1 ? "s" : ""}{" "}
            {selectedCategories.length > 0 && `(filtered by ${selectedCategories.length} categories)`}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Toggle Category Chart */}
          <button
            type="button"
            onClick={() => setShowChart((v) => !v)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control text-xs font-medium border border-border-subtle transition-colors ${
              showChart
                ? "bg-surface-secondary text-action-primary"
                : "bg-surface text-text-secondary hover:text-text-primary"
            }`}
            aria-label="Toggle Category Chart"
          >
            <ChartIcon size={14} />
            <span>{showChart ? "Hide Chart" : "Show Chart"}</span>
          </button>

          {/* Type Filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className={selectBase}
            aria-label="Filter by type"
          >
            <option value="">All Types</option>
            {TYPES.filter(Boolean).map((t) => (
              <option key={t} value={t}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Embedded Category-Wise Chart ── */}
      {showChart && categorySummary.categories.length > 0 && (
        <CategoryBreakdownChart
          categoryData={categorySummary.categories}
          totalExpense={categorySummary.total_expense}
          selectedCategories={selectedCategories}
          onToggleCategory={toggleCategory}
        />
      )}

      {/* ── Category Multi-Select & Combine Panel ── */}
      <div className="rounded-card bg-surface border border-border-subtle p-3.5 sm:p-4 shadow-card space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers size={15} className="text-action-primary" />
            <span className="text-xs font-medium text-text-primary">
              Combine Categories to Check Expense
            </span>
          </div>
          {selectedCategories.length > 0 && (
            <button
              type="button"
              onClick={clearCategorySelection}
              className="text-xs text-text-secondary hover:text-status-anomaly transition-colors"
            >
              Clear filter
            </button>
          )}
        </div>

        {/* Category Chips Multi-Select */}
        <div className="flex flex-wrap gap-1.5 sm:gap-2">
          {ALL_CATEGORIES.map((cat) => {
            const isSelected = selectedCategories.includes(cat.id);
            const color = getCategoryColor(cat.id);
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => toggleCategory(cat.id)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-control text-xs font-medium transition-all ${
                  isSelected
                    ? "bg-surface-secondary text-text-primary border border-action-primary ring-1 ring-action-primary/30"
                    : "bg-surface-secondary/50 text-text-secondary border border-border-subtle hover:text-text-primary hover:bg-surface-secondary"
                }`}
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span>{cat.label}</span>
                {isSelected ? (
                  <Check size={12} className="text-action-primary ml-0.5" />
                ) : null}
              </button>
            );
          })}
        </div>

        {/* ── Combined Category Expense Analysis Card ── */}
        {combinedStats && (
          <div className="mt-2.5 p-3 rounded-control bg-surface-secondary border border-action-primary/30 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div className="text-[11px] uppercase tracking-wider text-text-secondary font-medium">
                Combined Expense ({selectedCategories.join(" + ")})
              </div>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-base sm:text-lg font-mono font-bold text-action-primary">
                  {formatCurrency(combinedStats.amount)}
                </span>
                <span className="text-xs text-text-secondary">
                  ({combinedStats.percentage}% of all expenses)
                </span>
              </div>
            </div>
            <div className="text-xs text-text-secondary">
              <span className="font-mono font-medium text-text-primary">
                {combinedStats.count}
              </span>{" "}
              transaction{combinedStats.count !== 1 ? "s" : ""} in selected categories
            </div>
          </div>
        )}
      </div>

      {/* ── Transactions Table ── */}
      {transactions.length === 0 ? (
        <EmptyState
          title="No transactions found"
          message={
            selectedCategories.length > 0 || filterType
              ? "Try adjusting your category or type filters to see more results."
              : "No transactions have been recorded yet."
          }
          actionLabel={
            selectedCategories.length > 0 || filterType ? undefined : "Add Expense"
          }
          onAction={
            selectedCategories.length > 0 || filterType ? undefined : () => navigate("/add")
          }
        />
      ) : (
        <>
          <div className="rounded-card bg-surface border border-border-subtle shadow-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border-subtle bg-surface-secondary/50">
                    <th className="text-left px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                      Date
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                      Name
                    </th>
                    <th className="text-right px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                      Amount
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider hidden md:table-cell">
                      Category
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider hidden lg:table-cell">
                      Account
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider hidden sm:table-cell">
                      Type
                    </th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                      Status
                    </th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider w-16">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => (
                    <tr
                      key={tx.id}
                      className="border-b border-border-subtle last:border-0 hover:bg-surface-secondary/30 transition-colors"
                    >
                      <td className="px-4 py-3 text-text-secondary whitespace-nowrap">
                        {formatDate(tx.date)}
                      </td>
                      <td className="px-4 py-3 text-text-primary font-medium truncate max-w-[180px]">
                        {tx.name}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-text-primary whitespace-nowrap">
                        {formatCurrency(tx.amount)}
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        {tx.type === "transfer" ? (
                          <span className="text-xs text-text-secondary">Transfer</span>
                        ) : (
                          <CategoryPill category={tx.category} />
                        )}
                      </td>
                      <td className="px-4 py-3 text-text-secondary hidden lg:table-cell">
                        {tx.type === "transfer" ? (
                          <span className="inline-flex items-center gap-1 whitespace-nowrap">
                            {tx.account}
                            <span aria-hidden="true">→</span>
                            {tx.to_account || "—"}
                          </span>
                        ) : (
                          tx.account
                        )}
                      </td>
                      <td className="px-4 py-3 text-text-secondary capitalize hidden sm:table-cell">
                        {tx.type}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <AnomalyBadge status={tx.anomaly_status} />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => setDeleteTarget(tx)}
                          className="p-1.5 rounded-control text-text-secondary hover:text-status-anomaly hover:bg-status-anomaly/10 transition-colors"
                          aria-label={`Delete transaction: ${tx.name}`}
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Load More */}
          {hasMore && (
            <div className="flex justify-center">
              <button
                onClick={() => loadData(false)}
                disabled={loadingMore}
                className="px-6 py-2.5 rounded-control border border-border-subtle text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-secondary disabled:opacity-50 transition-colors"
              >
                {loadingMore
                  ? "Loading…"
                  : `Load More (${transactions.length} of ${totalCount})`}
              </button>
            </div>
          )}
        </>
      )}

      {/* Delete confirmation */}
      <ConfirmModal
        open={!!deleteTarget}
        title="Delete Transaction"
        message={`Are you sure you want to delete "${deleteTarget?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />

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
