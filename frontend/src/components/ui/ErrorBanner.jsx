import { AlertTriangle, RefreshCw } from "lucide-react";

/**
 * ErrorBanner — API failure notice with optional retry action.
 */
export default function ErrorBanner({ message, onRetry }) {
  return (
    <div
      className="flex items-start gap-3 p-4 rounded-card bg-status-anomaly/10 border border-status-anomaly/20"
      role="alert"
    >
      <AlertTriangle
        size={18}
        className="text-status-anomaly mt-0.5 shrink-0"
        strokeWidth={2}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text-primary font-medium">
          Something went wrong
        </p>
        <p className="text-xs text-text-secondary mt-0.5">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control text-xs font-medium text-status-anomaly hover:bg-status-anomaly/10 transition-colors shrink-0"
        >
          <RefreshCw size={12} />
          Retry
        </button>
      )}
    </div>
  );
}
