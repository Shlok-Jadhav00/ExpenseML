import { AlertTriangle } from "lucide-react";

/**
 * ConfirmModal — Accessible confirmation dialog for destructive actions.
 */
export default function ConfirmModal({
  open,
  title = "Confirm action",
  message = "Are you sure? This cannot be undone.",
  confirmLabel = "Delete",
  onConfirm,
  onCancel,
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onCancel}
        aria-hidden="true"
      />
      {/* Dialog */}
      <div
        className="relative bg-surface border border-border-subtle rounded-card shadow-card p-6 w-full max-w-sm"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-desc"
      >
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-status-anomaly/15 flex items-center justify-center shrink-0">
            <AlertTriangle size={20} className="text-status-anomaly" />
          </div>
          <div>
            <h2
              id="confirm-title"
              className="text-base font-semibold text-text-primary"
            >
              {title}
            </h2>
            <p
              id="confirm-desc"
              className="text-sm text-text-secondary mt-1"
            >
              {message}
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-control text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 rounded-control bg-status-anomaly text-white text-sm font-semibold hover:bg-status-anomaly/85 transition-colors"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
