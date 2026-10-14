import { Inbox } from "lucide-react";

/**
 * EmptyState — Friendly zero-data placeholder.
 *
 * Renders an icon, title, message, and an optional call-to-action button.
 */
export default function EmptyState({
  icon: Icon = Inbox,
  title = "Nothing here yet",
  message = "",
  actionLabel,
  onAction,
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="w-14 h-14 rounded-full bg-surface-secondary flex items-center justify-center mb-4">
        <Icon size={24} className="text-text-secondary" strokeWidth={1.5} />
      </div>
      <h3 className="text-base font-semibold text-text-primary mb-1">
        {title}
      </h3>
      {message && (
        <p className="text-sm text-text-secondary max-w-sm mb-4">{message}</p>
      )}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-control bg-action-primary text-background text-sm font-semibold hover:bg-action-primary/85 transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
