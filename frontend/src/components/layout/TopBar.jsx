import { useNavigate } from "react-router-dom";
import { Menu, Plus } from "lucide-react";
import { getGreeting, getTodayFormatted } from "../../lib/formatters";

export default function TopBar({ onMenuToggle }) {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between h-16 px-4 md:px-6 bg-surface/80 backdrop-blur-md border-b border-border-subtle">
      {/* Left: mobile menu + greeting */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-control text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu size={20} />
        </button>
        <div>
          <h1 className="text-sm md:text-base font-semibold text-text-primary leading-tight">
            {getGreeting()}
          </h1>
          <p className="text-xs text-text-secondary">{getTodayFormatted()}</p>
        </div>
      </div>

      {/* Right: quick add button */}
      <button
        onClick={() => navigate("/add")}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-control bg-action-primary text-background text-sm font-semibold hover:bg-action-primary/85 active:scale-[0.97] transition-all"
      >
        <Plus size={16} strokeWidth={2.5} />
        <span className="hidden sm:inline">Add Expense</span>
      </button>
    </header>
  );
}
