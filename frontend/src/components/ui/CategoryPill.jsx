import { getCategoryColor } from "../../lib/categoryColors";

/**
 * CategoryPill — coloured category chip.
 *
 * Uses the centralized categoryColors map so every instance of
 * a category across the app displays in the same colour.
 */
export default function CategoryPill({ category }) {
  const color = getCategoryColor(category);

  return (
    <span
      className="inline-flex items-center px-2.5 py-0.5 rounded-badge text-xs font-medium whitespace-nowrap"
      style={{
        backgroundColor: `${color}20`,
        color: color,
      }}
    >
      {category}
    </span>
  );
}
