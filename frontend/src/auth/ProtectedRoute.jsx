import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/auth/AuthContext';

/**
 * Gate any authenticated-only route. If the user is not logged in they bounce
 * to /login and we preserve the intended destination in location.state so the
 * login page can send them back after a successful sign-in.
 *
 * ``requireAdmin`` layers a role check on top without needing a separate guard
 * component — callers just add ``requireAdmin`` to the prop bag.
 */
export default function ProtectedRoute({ children, requireAdmin = false }) {
  const { isAuthenticated, isLoading, isAdmin } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-sm text-gray-500">Loading…</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
