import { useState } from "react";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { BarChart3, PieChart as PieIcon } from "lucide-react";
import CategoryDonut from "./CategoryDonut";
import { getCategoryColor } from "../../lib/categoryColors";
import { formatCurrency } from "../../lib/formatters";

/**
 * Custom tooltip for the Category Bar Graph
 */
function CustomBarTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload;
  const color = getCategoryColor(data.name);

  return (
    <div className="bg-surface border border-border-subtle rounded-control px-3.5 py-2.5 shadow-card space-y-1">
      <div className="flex items-center gap-2">
        <span
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: color }}
        />
        <span className="text-xs font-semibold text-text-primary">
          {data.name}
        </span>
      </div>
      <div className="flex items-baseline gap-2 pt-0.5">
        <span className="text-sm font-mono font-bold text-text-primary">
          {formatCurrency(data.value)}
        </span>
        <span className="text-xs text-text-secondary">
          ({data.percentage}%)
        </span>
      </div>
      <p className="text-[11px] text-text-secondary">
        {data.count} transaction{data.count !== 1 ? "s" : ""}
      </p>
    </div>
  );
}

/**
 * CategoryBreakdownChart
 *
 * Dedicated expense category graph component:
 * - Real Recharts Bar Chart graphing individual categories (Food, Travel/Transport, Shopping, etc.)
 * - Donut chart view toggle
 * - Visual highlighting of combined / selected categories
 * - Category cards/chips showing exact spend and percentage
 */
export default function CategoryBreakdownChart({
  categoryData = [],
  totalExpense = 0,
  selectedCategories = [],
  onToggleCategory,
}) {
  const [chartView, setChartView] = useState("bar"); // "bar" | "donut"

  if (!categoryData || categoryData.length === 0) {
    return null;
  }

  return (
    <div className="rounded-card bg-surface border border-border-subtle p-4 sm:p-5 shadow-card space-y-4">
      {/* ── Graph Header & View Toggle ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-border-subtle">
        <div>
          <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
            <BarChart3 size={16} className="text-action-primary" />
            <span>Expense Category Graph</span>
          </h2>
          <p className="text-xs text-text-secondary mt-0.5">
            Spending across categories (Food, Travel, Shopping, etc.) • Total:{" "}
            <span className="font-mono font-medium text-text-primary">
              {formatCurrency(totalExpense)}
            </span>
          </p>
        </div>

        {/* View Switcher: Bar Graph vs Donut */}
        <div className="inline-flex rounded-control bg-surface-secondary p-0.5 border border-border-subtle self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setChartView("bar")}
            className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-control transition-colors ${
              chartView === "bar"
                ? "bg-action-primary text-background font-semibold shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            }`}
            aria-label="Bar Graph View"
          >
            <BarChart3 size={13} />
            <span>Category Graph</span>
          </button>
          <button
            type="button"
            onClick={() => setChartView("donut")}
            className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-control transition-colors ${
              chartView === "donut"
                ? "bg-action-primary text-background font-semibold shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            }`}
            aria-label="Donut Chart View"
          >
            <PieIcon size={13} />
            <span>Donut Chart</span>
          </button>
        </div>
      </div>

      {/* ── Active Chart View ── */}
      {chartView === "donut" ? (
        <div className="pt-2">
          <CategoryDonut data={categoryData} />
        </div>
      ) : (
        <div className="pt-2">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={categoryData}
              margin={{ top: 12, right: 10, left: -10, bottom: 25 }}
              onClick={(state) => {
                if (state && state.activePayload && state.activePayload.length) {
                  const clickedCat = state.activePayload[0].payload.name;
                  if (onToggleCategory) onToggleCategory(clickedCat);
                }
              }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.06)"
                vertical={false}
              />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11, fill: "#94A3B8" }}
                axisLine={false}
                tickLine={false}
                interval={0}
                angle={-18}
                textAnchor="end"
                height={35}
              />
              <YAxis
                tickFormatter={(v) => `₹${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`}
                tick={{ fontSize: 11, fill: "#94A3B8" }}
                axisLine={false}
                tickLine={false}
                width={48}
              />
              <Tooltip content={<CustomBarTooltip />} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]} cursor="pointer">
                {categoryData.map((entry, index) => {
                  const isHighlighted =
                    selectedCategories.length === 0 ||
                    selectedCategories.includes(entry.name);
                  return (
                    <Cell
                      key={`cell-${index}`}
                      fill={getCategoryColor(entry.name)}
                      opacity={isHighlighted ? 1 : 0.25}
                    />
                  );
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Category Breakdown Legend / Pill List ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 pt-1 border-t border-border-subtle">
        {categoryData.map((item) => {
          const isSelected = selectedCategories.includes(item.name);
          const color = getCategoryColor(item.name);

          return (
            <button
              key={item.name}
              type="button"
              onClick={() => onToggleCategory && onToggleCategory(item.name)}
              className={`flex flex-col p-2 rounded-control text-left transition-all ${
                isSelected
                  ? "bg-surface-secondary border border-action-primary ring-1 ring-action-primary/30"
                  : "bg-surface-secondary/40 border border-border-subtle hover:bg-surface-secondary/70"
              }`}
            >
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 font-medium text-text-primary truncate">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  {item.name}
                </span>
                <span className="text-[11px] font-mono text-text-secondary">
                  {item.percentage}%
                </span>
              </div>
              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-xs font-mono font-semibold text-text-primary">
                  {formatCurrency(item.value)}
                </span>
                <span className="text-[10px] text-text-secondary">
                  {item.count} items
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
