import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserCircle, Trash2 } from "lucide-react";
import { useAuth } from "../lib/AuthContext";
import Toast from "../components/ui/Toast";

export default function Account() {
  const navigate = useNavigate();
  const { user, deleteAccount } = useAuth();
  const [showDelete, setShowDelete] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState(null);

  async function handleDelete(e) {
    e.preventDefault();
    if (!password.trim()) {
      setError("Password is required to confirm account deletion");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await deleteAccount(password);
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const inputBase =
    "w-full px-3 py-2.5 rounded-control bg-surface-secondary border border-border-subtle text-text-primary text-sm placeholder:text-text-secondary/60 focus:outline-none focus:ring-2 focus:ring-focus-ring transition-colors";

  return (
    <div className="max-w-xl mx-auto space-y-6">
      {/* Account Info */}
      <div className="rounded-card bg-surface border border-border-subtle shadow-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <UserCircle size={20} className="text-action-primary" />
          <h1 className="text-lg font-semibold text-text-primary">Account</h1>
        </div>

        <div className="space-y-3">
          <div>
            <p className="text-xs font-medium text-text-secondary mb-1">
              Email
            </p>
            <p className="text-sm text-text-primary font-mono">
              {user?.email}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-text-secondary mb-1">
              User ID
            </p>
            <p className="text-sm text-text-primary font-mono truncate">
              {user?.id}
            </p>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="rounded-card bg-surface border border-status-anomaly/20 shadow-card p-6">
        <div className="flex items-center gap-3 mb-2">
          <Trash2 size={18} className="text-status-anomaly" />
          <h2 className="text-base font-semibold text-text-primary">
            Danger Zone
          </h2>
        </div>
        <p className="text-sm text-text-secondary mb-4">
          Deleting your account permanently removes all your transactions,
          forecasting history, and personal data. This action cannot be undone.
        </p>

        {!showDelete ? (
          <button
            onClick={() => setShowDelete(true)}
            className="px-4 py-2.5 rounded-control border border-status-anomaly/30 text-sm font-medium text-status-anomaly hover:bg-status-anomaly/10 transition-colors"
          >
            Delete my account
          </button>
        ) : (
          <form onSubmit={handleDelete} className="space-y-4">
            {error && (
              <div className="p-3 rounded-control bg-status-anomaly/10 border border-status-anomaly/20 text-sm text-status-anomaly">
                {error}
              </div>
            )}

            <div>
              <label
                htmlFor="delete-password"
                className="block text-xs font-medium text-text-secondary mb-1.5"
              >
                Confirm your password to proceed
              </label>
              <input
                id="delete-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your current password"
                className={inputBase}
                required
              />
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowDelete(false);
                  setPassword("");
                  setError(null);
                }}
                className="px-4 py-2 rounded-control text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 rounded-control bg-status-anomaly text-white text-sm font-semibold hover:bg-status-anomaly/85 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting
                  ? "Deleting…"
                  : "Permanently delete my account"}
              </button>
            </div>
          </form>
        )}
      </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
