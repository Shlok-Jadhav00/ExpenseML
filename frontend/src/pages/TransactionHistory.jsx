import { useState, useEffect, useCallback } from "react";
import { Trash2 } from "lucide-react";
import { fetchTransactions, deleteTransaction } from "../lib/api";
import { formatCurrency, formatDate } from "../lib/formatters";
import AnomalyBadge from "../components/ui/AnomalyBadge";
import CategoryPill from "../components/ui/CategoryPill";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import ConfirmModal from "../components/ui/ConfirmModal";
import Toast from "../components/ui/Toast";
import { useNavigate } from "react-router-dom";

const PAGE_SIZE = 20;
const CATEGORIES = ["", "Food", "Shopping", "Transport", "Entertainment", "Education", "Bills", "Other"];
const TYPES = ["", "expense", "income", "transfer"];

export default function TransactionHistory() {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [filterCategory, setFilterCategory] = useState("");
  const [filterType, setFilterType] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [toast, setToast] = useState(null);

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
          category: filterCategory || undefined,
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
    [offset, filterCategory, filterType]
  );

  /* Load on mount and when filters change */
  useEffect(() => {
    setOffset(0);
    setTransactions([]);
    loadData(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterCategory, filterType]);

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteTransaction(deleteTarget.id);
      setTransactions((prev) =>
        prev.filter((t) => t.id !== deleteTarget.id)
      );
      setTotalCount((prev) => prev - 1);
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
    "px-3 py-2 rounded-control bg-surface-secondary border border-border-subtle text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-focus-ring";

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="animate-skeleton h-10 w-64 rounded-control" />
        <LoadingSpinner variant="table" />
      </div>
    );
  }

  if (error) {
    return <ErrorBanner message={error} onRetry={() => loadData(true)} />;
  }

  return (
    <div className="space-y-5">
      {/* Header + Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">
            Transaction History
          </h1>
          <p className="text-xs text-text-secondary mt-0.5">
            {totalCount} transaction{totalCount !== 1 ? "s" : ""} total
          </p>
        </div>
        <div className="flex gap-3">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className={selectBase}
            aria-label="Filter by category"
          >
            <option value="">All Categories</option>
            {CATEGORIES.filter(Boolean).map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
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

      {/* Empty state */}
      {transactions.length === 0 ? (
        <EmptyState
          title="No transactions found"
          message={
            filterCategory || filterType
              ? "Try adjusting your filters to see more results."
              : "No transactions have been recorded yet."
          }
          actionLabel={
            filterCategory || filterType ? undefined : "Add Expense"
          }
          onAction={
            filterCategory || filterType
              ? undefined
              : () => navigate("/add")
          }
        />
      ) : (
        <>
          {/* Table */}
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
                        <CategoryPill category={tx.category} />
                      </td>
                      <td className="px-4 py-3 text-text-secondary hidden lg:table-cell">
                        {tx.account}
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
                {loadingMore ? "Loading…" : `Load More (${transactions.length} of ${totalCount})`}
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
