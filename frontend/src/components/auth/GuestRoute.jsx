import { Navigate } from "react-router-dom";
import { useAuth } from "../../lib/AuthContext";
import LoadingSpinner from "../ui/LoadingSpinner";

/**
 * GuestRoute — redirects to the dashboard when the user is already logged in.
 * Prevents authenticated users from seeing login/register pages.
 */
export default function GuestRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <LoadingSpinner variant="inline" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
}
