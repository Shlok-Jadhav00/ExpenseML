import { CheckCircle, XCircle, X } from "lucide-react";
import { useEffect } from "react";

/**
 * Toast — ephemeral notification for form submissions.
 *
 * Automatically dismisses after 4 seconds.
 */
export default function Toast({ message, type = "success", onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const isSuccess = type === "success";

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-card shadow-card border ${
        isSuccess
          ? "bg-surface border-status-normal/30"
          : "bg-surface border-status-anomaly/30"
      }`}
      role="status"
      aria-live="polite"
    >
      {isSuccess ? (
        <CheckCircle size={18} className="text-status-normal shrink-0" />
      ) : (
        <XCircle size={18} className="text-status-anomaly shrink-0" />
      )}
      <p className="text-sm text-text-primary">{message}</p>
      <button
        onClick={onClose}
        className="p-1 text-text-secondary hover:text-text-primary transition-colors shrink-0"
        aria-label="Dismiss notification"
      >
        <X size={14} />
      </button>
    </div>
  );
}
