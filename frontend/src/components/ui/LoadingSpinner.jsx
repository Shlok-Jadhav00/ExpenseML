/**
 * LoadingSpinner — Full-area loading indicator with animated skeleton blocks.
 *
 * Accepts a `variant` prop for different loading contexts:
 * - "cards"   : Row of 4 skeleton metric cards
 * - "table"   : Skeleton table rows
 * - "page"    : Centered spinner
 * - "inline"  : Small inline spinner
 */
export default function LoadingSpinner({ variant = "page" }) {
  if (variant === "cards") {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="rounded-card bg-surface border border-border-subtle p-5 space-y-3"
          >
            <div className="animate-skeleton h-3 w-20 rounded" />
            <div className="animate-skeleton h-8 w-28 rounded" />
            <div className="animate-skeleton h-3 w-16 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="animate-skeleton h-12 w-full rounded-control"
          />
        ))}
      </div>
    );
  }

  if (variant === "inline") {
    return (
      <div className="inline-flex items-center gap-2 text-text-secondary text-sm">
        <svg
          className="animate-spin h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
            strokeDasharray="31.4 31.4"
            strokeLinecap="round"
          />
        </svg>
        Loading…
      </div>
    );
  }

  /* Default: page-level centered spinner */
  return (
    <div className="flex items-center justify-center py-20" role="status" aria-label="Loading">
      <div className="flex flex-col items-center gap-3">
        <svg
          className="animate-spin h-8 w-8 text-action-primary"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
            strokeDasharray="31.4 31.4"
            strokeLinecap="round"
          />
        </svg>
        <span className="text-sm text-text-secondary">Loading…</span>
      </div>
    </div>
  );
}
