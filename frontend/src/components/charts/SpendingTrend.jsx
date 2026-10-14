import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { formatCurrency, formatShortDate } from "../../lib/formatters";

/**
 * SpendingTrend — Recharts AreaChart of daily spending over time.
 *
 * Uses sage-based neutral fill to represent normal spending patterns.
 * Renders nothing when data is empty.
 */

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-surface border border-border-subtle rounded-control px-3 py-2 shadow-card">
      <p className="text-xs text-text-secondary">{formatShortDate(label)}</p>
      <p className="text-sm font-mono font-semibold text-text-primary">
        {formatCurrency(payload[0].value)}
      </p>
    </div>
  );
}

export default function SpendingTrend({ data }) {
  if (!data || data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10B981" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#10B981" stopOpacity={0.0} />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="rgba(255,255,255,0.06)"
          vertical={false}
        />
        <XAxis
          dataKey="date"
          tickFormatter={formatShortDate}
          tick={{ fontSize: 11, fill: "#94A3B8" }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={(v) => `₹${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`}
          tick={{ fontSize: 11, fill: "#94A3B8" }}
          axisLine={false}
          tickLine={false}
          width={50}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="amount"
          stroke="#10B981"
          strokeWidth={2.5}
          fill="url(#spendGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
