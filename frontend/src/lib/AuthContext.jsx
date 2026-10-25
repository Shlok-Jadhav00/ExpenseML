import { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  authMe,
  authLogin,
  authRegister,
  authLogout,
  authDeleteAccount,
  clearCsrfToken,
  fetchCsrfToken,
} from "./api";

const AuthContext = createContext(null);

/**
 * AuthProvider — wraps the app and provides authentication state.
 *
 * On mount, attempts to restore the session via GET /auth/me.
 * Exposes login, register, logout, deleteAccount, and user state.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /* Restore session on mount */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await authMe();
        if (!cancelled) {
          setUser(data.user);
          /* Pre-fetch CSRF token for future mutations */
          fetchCsrfToken().catch(() => {});
        }
      } catch {
        /* Not logged in — this is expected for new visitors */
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const data = await authLogin(email, password);
      setUser(data.user);
      /* Pre-fetch CSRF token after login */
      fetchCsrfToken().catch(() => {});
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  const register = useCallback(async (email, password) => {
    setError(null);
    try {
      const data = await authRegister(email, password);
      setUser(data.user);
      /* Pre-fetch CSRF token after registration */
      fetchCsrfToken().catch(() => {});
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await authLogout();
    } catch {
      /* If logout fails server-side, still clear client state */
    } finally {
      setUser(null);
      clearCsrfToken();
    }
  }, []);

  const deleteAccount = useCallback(async (password) => {
    await authDeleteAccount(password);
    setUser(null);
    clearCsrfToken();
  }, []);

  /** Called when any API response returns 401 — forces client-side logout */
  const handleSessionExpired = useCallback(() => {
    setUser(null);
    clearCsrfToken();
  }, []);

  const value = {
    user,
    loading,
    error,
    setError,
    login,
    register,
    logout,
    deleteAccount,
    handleSessionExpired,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * useAuth — access auth state and actions from any component.
 */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
