import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { authAPI, authTokenStore, registerUnauthorizedHandler } from '@/utils/api';

/**
 * AuthContext — single source of truth for "who is logged in?".
 *
 * Responsibilities:
 *   - Hydrate state from the persisted JWT on mount (so refresh doesn't log out).
 *   - Expose login / logout.
 *   - Translate 401/403 from any API call into a clean logout + redirect signal.
 *
 * Everything else in the UI reads ``user`` and ``status`` and derives what to show.
 */

const AuthContext = createContext(null);

const STATUS = {
  LOADING: 'loading',
  AUTHENTICATED: 'authenticated',
  UNAUTHENTICATED: 'unauthenticated',
};

export function AuthProvider({ children }) {
  const [status, setStatus] = useState(STATUS.LOADING);
  const [user, setUser] = useState(null);
  const [error, setError] = useState(null);

  const logout = useCallback(async ({ callServer = true } = {}) => {
    if (callServer) {
      try {
        await authAPI.logout();
      } catch {
        /* Intentional no-op: stateless logout. */
      }
    }
    authTokenStore.clear();
    setUser(null);
    setStatus(STATUS.UNAUTHENTICATED);
  }, []);

  // Centralized unauthorized handler for every API call in the app.
  useEffect(() => {
    registerUnauthorizedHandler(() => {
      // api.js already cleared the token; mirror that in React state.
      setUser(null);
      setStatus(STATUS.UNAUTHENTICATED);
    });
    return () => registerUnauthorizedHandler(null);
  }, []);

  // Hydrate from localStorage on boot.
  useEffect(() => {
    const token = authTokenStore.get();
    if (!token) {
      setStatus(STATUS.UNAUTHENTICATED);
      return;
    }
    let cancelled = false;
    authAPI
      .me()
      .then((res) => {
        if (cancelled) return;
        setUser(res.data);
        setStatus(STATUS.AUTHENTICATED);
      })
      .catch(() => {
        if (cancelled) return;
        authTokenStore.clear();
        setUser(null);
        setStatus(STATUS.UNAUTHENTICATED);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loginWithGoogle = useCallback(async (googleIdToken) => {
    setError(null);
    try {
      const res = await authAPI.loginWithGoogle(googleIdToken);
      authTokenStore.set(res.data.access_token);
      setUser(res.data.user);
      setStatus(STATUS.AUTHENTICATED);
      return { ok: true, user: res.data.user };
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        'Sign-in failed. Please try again.';
      setError(String(detail));
      return { ok: false, error: String(detail) };
    }
  }, []);

  const value = useMemo(
    () => ({
      status,
      user,
      error,
      isAuthenticated: status === STATUS.AUTHENTICATED,
      isLoading: status === STATUS.LOADING,
      isAdmin: user?.role === 'admin',
      loginWithGoogle,
      logout,
      clearError: () => setError(null),
    }),
    [status, user, error, loginWithGoogle, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
}

export { STATUS as AuthStatus };
