import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  PlusCircle,
  List,
  BrainCircuit,
  X,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/add", label: "Add Expense", icon: PlusCircle },
  { to: "/history", label: "History", icon: List },
  { to: "/insights", label: "ML Insights", icon: BrainCircuit },
];

export default function Sidebar({ open, onClose }) {
  return (
    <aside
      className={`
        fixed inset-y-0 left-0 z-40 w-60 flex flex-col
        bg-surface border-r border-border-subtle
        transition-transform duration-200 ease-in-out
        lg:translate-x-0
        ${open ? "translate-x-0" : "-translate-x-full"}
      `}
      aria-label="Main navigation"
    >
      {/* Brand header */}
      <div className="flex items-center justify-between h-16 px-5 border-b border-border-subtle">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-action-primary flex items-center justify-center">
            <span className="text-background font-bold text-sm">E</span>
          </div>
          <span className="text-text-primary font-semibold text-lg tracking-tight">
            ExpenseML
          </span>
        </div>
        <button
          onClick={onClose}
          className="lg:hidden p-1.5 rounded-control text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          aria-label="Close navigation"
        >
          <X size={20} />
        </button>
      </div>

      {/* Navigation links */}
      <nav className="flex-1 px-3 py-4 space-y-1" role="navigation">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-control text-sm font-medium transition-colors ${
                isActive
                  ? "bg-action-primary/15 text-action-primary"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-secondary"
              }`
            }
          >
            <Icon size={18} strokeWidth={1.8} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-border-subtle">
        <p className="text-xs text-text-secondary leading-relaxed">
          Campus Capital Intelligence
        </p>
      </div>
    </aside>
  );
}
