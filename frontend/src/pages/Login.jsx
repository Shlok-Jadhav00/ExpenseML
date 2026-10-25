import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";
import { useAuth } from "../lib/AuthContext";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(form.email, form.password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const inputBase =
    "w-full px-3 py-2.5 rounded-control bg-surface-secondary border border-border-subtle text-text-primary text-sm placeholder:text-text-secondary/60 focus:outline-none focus:ring-2 focus:ring-focus-ring transition-colors";

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="w-10 h-10 rounded-lg bg-action-primary flex items-center justify-center">
            <span className="text-background font-bold text-lg">E</span>
          </div>
          <span className="text-text-primary font-semibold text-xl tracking-tight">
            ExpenseML
          </span>
        </div>

        <div className="rounded-card bg-surface border border-border-subtle shadow-card p-6">
          <h1 className="text-lg font-semibold text-text-primary mb-1">
            Welcome back
          </h1>
          <p className="text-sm text-text-secondary mb-6">
            Sign in to your account to continue.
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-control bg-status-anomaly/10 border border-status-anomaly/20 text-sm text-status-anomaly">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label
                htmlFor="login-email"
                className="block text-xs font-medium text-text-secondary mb-1.5"
              >
                Email
              </label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={(e) =>
                  setForm((p) => ({ ...p, email: e.target.value }))
                }
                placeholder="you@example.com"
                className={inputBase}
                required
              />
            </div>
            <div>
              <label
                htmlFor="login-password"
                className="block text-xs font-medium text-text-secondary mb-1.5"
              >
                Password
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={form.password}
                onChange={(e) =>
                  setForm((p) => ({ ...p, password: e.target.value }))
                }
                placeholder="••••••••••••"
                className={inputBase}
                required
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-control bg-action-primary text-background font-semibold text-sm hover:bg-action-primary/85 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <LogIn size={16} strokeWidth={2} />
              {submitting ? "Signing in…" : "Sign In"}
            </button>
          </form>

          <p className="text-center text-sm text-text-secondary mt-5">
            Don&apos;t have an account?{" "}
            <Link
              to="/register"
              className="text-action-primary hover:text-action-primary/80 font-medium transition-colors"
            >
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
