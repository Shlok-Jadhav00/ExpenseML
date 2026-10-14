/**
 * Shared category → colour map.
 *
 * Used by CategoryDonut, CategoryPill, and TransactionHistory so that
 * every category always appears in the same colour across the whole app.
 *
 * Colours are muted, harmonious shades that do NOT overlap with the
 * semantic status palette (sage/champagne/coral).
 */

const CATEGORY_COLORS = {
  Food: "#10B981",
  Shopping: "#8B5CF6",
  Transport: "#06B6D4",
  Entertainment: "#EC4899",
  Education: "#3B82F6",
  Bills: "#F59E0B",
  Other: "#64748B",
};

/**
 * Returns the mapped colour for a category, falling back to a neutral slate.
 */
export function getCategoryColor(category) {
  return CATEGORY_COLORS[category] || "#64748B";
}

/**
 * Returns all category names that have explicit colour mappings.
 */
export function getCategoryNames() {
  return Object.keys(CATEGORY_COLORS);
}

export default CATEGORY_COLORS;
