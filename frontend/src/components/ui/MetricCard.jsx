/**
 * MetricCard — Reusable KPI summary card.
 *
 * Renders a labelled value with an icon and optional status badge.
 * Uses Quiet Wealth surface/border tokens.
 */
export default function MetricCard({ title, value, icon: Icon, badge, subtitle }) {
  return (
    <div className="rounded-card bg-surface border border-border-subtle shadow-card p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-text-secondary font-medium">
          {title}
        </span>
        {Icon && (
          <div className="w-9 h-9 rounded-control bg-surface-secondary flex items-center justify-center">
            <Icon size={18} className="text-action-primary" strokeWidth={1.8} />
          </div>
        )}
      </div>
      <div>
        <p className="text-2xl font-bold font-mono text-text-primary leading-none">
          {value}
        </p>
        {subtitle && (
          <p className="mt-1.5 text-xs text-text-secondary">{subtitle}</p>
        )}
      </div>
      {badge && (
        <span
          className={`inline-flex self-start items-center gap-1.5 px-2.5 py-1 rounded-badge text-xs font-medium ${badge.className || "bg-surface-secondary text-text-secondary"}`}
        >
          {badge.icon && <badge.icon size={12} />}
          {badge.label}
        </span>
      )}
    </div>
  );
}
