import { Navigate } from "react-router-dom";
import { useAuth } from "../../lib/AuthContext";
import LoadingSpinner from "../ui/LoadingSpinner";

/**
 * ProtectedRoute — redirects to /login when the user is not authenticated.
 * Shows a loading spinner while the initial session check is in progress.
 */
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <LoadingSpinner variant="inline" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
