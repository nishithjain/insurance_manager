import React, { useCallback, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/auth/AuthContext';
import GoogleSignInButton from '@/auth/GoogleSignInButton';

/**
 * Sign-in screen.
 *
 * Only path in: Google Sign-In. After the backend exchanges the Google ID
 * token for our own JWT, AuthContext is updated and we navigate back to
 * wherever the user was trying to go (stored in location.state.from by
 * ProtectedRoute), falling back to the dashboard.
 */
export default function Login() {
  const { isAuthenticated, loginWithGoogle } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  const from = location.state?.from || '/dashboard';

  const handleCredential = useCallback(
    async (idToken) => {
      setBusy(true);
      setError(null);
      const result = await loginWithGoogle(idToken);
      setBusy(false);
      if (!result.ok) {
        setError(result.error);
        return;
      }
      navigate(from, { replace: true });
    },
    [loginWithGoogle, navigate, from],
  );

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-indigo-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white shadow-xl p-8">
        <div className="flex items-center gap-3 mb-6">
          <img src="/InsuranceManager.png" alt="" className="h-11 w-11 rounded-xl object-cover shadow-sm" />
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Insurance Manager</h1>
            <p className="text-sm text-gray-500">Sign in to continue</p>
          </div>
        </div>

        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Sign in with your Google account. Access is restricted to Gmail addresses approved by
            an administrator.
          </p>

          <div className="flex justify-center pt-2">
            <GoogleSignInButton onCredential={handleCredential} onError={setError} disabled={busy} />
          </div>

          {busy && <p className="text-xs text-gray-500 text-center">Verifying with server…</p>}

          {error && (
            <div
              role="alert"
              className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900"
            >
              {error}
            </div>
          )}
        </div>

        <p className="mt-8 text-xs text-gray-400 text-center">
          If you've never signed in here before, ask an administrator to add your Gmail ID.
        </p>
      </div>
    </div>
  );
}
