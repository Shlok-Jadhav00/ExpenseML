import { ShieldCheck, ShieldAlert, ShieldOff } from "lucide-react";

/**
 * AnomalyBadge — Semantic status pill for ML inference results.
 *
 * Renders "Normal", "Anomaly", "Not Applicable", or "Error" with
 * the correct Quiet Wealth colour token and an accompanying icon
 * (status is never conveyed by colour alone).
 */

const VARIANTS = {
  Normal: {
    className: "bg-status-normal/15 text-status-normal",
    icon: ShieldCheck,
    label: "Normal",
  },
  Anomaly: {
    className: "bg-status-anomaly/15 text-status-anomaly",
    icon: ShieldAlert,
    label: "Anomaly",
  },
  "Not Applicable": {
    className: "bg-surface-secondary text-text-secondary",
    icon: ShieldOff,
    label: "N/A",
  },
  Error: {
    className: "bg-status-anomaly/15 text-status-anomaly",
    icon: ShieldAlert,
    label: "Error",
  },
};

export default function AnomalyBadge({ status }) {
  const variant = VARIANTS[status] || VARIANTS["Not Applicable"];
  const Icon = variant.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-badge text-xs font-medium whitespace-nowrap ${variant.className}`}
      role="status"
      aria-label={`Anomaly status: ${status || "Not Applicable"}`}
    >
      <Icon size={12} strokeWidth={2} />
      {variant.label}
    </span>
  );
}
