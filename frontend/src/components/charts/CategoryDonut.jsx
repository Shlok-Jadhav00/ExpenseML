import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { getCategoryColor } from "../../lib/categoryColors";
import { formatCurrency } from "../../lib/formatters";

/**
 * CategoryDonut — Recharts PieChart showing expense breakdown by category.
 *
 * Uses the shared categoryColors map for consistent per-category colouring.
 * Renders nothing (gracefully) when data is empty.
 */

function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const { name, value } = payload[0];
  return (
    <div className="bg-surface border border-border-subtle rounded-control px-3 py-2 shadow-card">
      <p className="text-xs text-text-secondary">{name}</p>
      <p className="text-sm font-mono font-semibold text-text-primary">
        {formatCurrency(value)}
      </p>
    </div>
  );
}

function renderLegend(props) {
  const { payload } = props;
  return (
    <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-2">
      {payload.map((entry, i) => (
        <span key={i} className="inline-flex items-center gap-1.5 text-xs text-text-secondary">
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: entry.color }}
          />
          {entry.value}
        </span>
      ))}
    </div>
  );
}

export default function CategoryDonut({ data }) {
  if (!data || data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="45%"
          innerRadius={55}
          outerRadius={90}
          paddingAngle={2}
          strokeWidth={0}
        >
          {data.map((entry, i) => (
            <Cell key={i} fill={getCategoryColor(entry.name)} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend content={renderLegend} />
      </PieChart>
    </ResponsiveContainer>
  );
}
