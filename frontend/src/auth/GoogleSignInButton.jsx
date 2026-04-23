import React, { useEffect, useRef, useState } from 'react';

/**
 * Renders the official Google Identity Services (GIS) sign-in button.
 *
 * The GIS library is loaded via a <script> tag in public/index.html. This
 * component waits for ``window.google`` to appear, then initializes the client
 * and mounts the button into our container div. When Google hands us an ID
 * token via the callback, we hand it up to the parent.
 *
 * Requires REACT_APP_GOOGLE_CLIENT_ID — the OAuth 2.0 Web Client ID from the
 * Google Cloud console. We surface a clear error instead of silently failing
 * when it's missing.
 */
export default function GoogleSignInButton({ onCredential, onError, disabled = false }) {
  const containerRef = useRef(null);
  const [ready, setReady] = useState(false);
  const [scriptError, setScriptError] = useState(null);

  const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId) {
      setScriptError(
        'Google Sign-In is not configured. Set REACT_APP_GOOGLE_CLIENT_ID in frontend/.env.',
      );
      return;
    }

    let cancelled = false;
    let pollTimer = null;

    const tryInit = () => {
      if (cancelled) return;
      const google = window.google;
      if (!google?.accounts?.id) {
        pollTimer = setTimeout(tryInit, 150);
        return;
      }
      google.accounts.id.initialize({
        client_id: clientId,
        callback: (resp) => {
          if (!resp?.credential) {
            onError?.('No credential returned by Google.');
            return;
          }
          onCredential?.(resp.credential);
        },
        ux_mode: 'popup',
        auto_select: false,
        itp_support: true,
      });
      if (containerRef.current) {
        google.accounts.id.renderButton(containerRef.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          shape: 'rectangular',
          logo_alignment: 'left',
          width: 280,
        });
      }
      setReady(true);
    };

    tryInit();

    return () => {
      cancelled = true;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [clientId, onCredential, onError]);

  if (scriptError) {
    return (
      <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
        {scriptError}
      </div>
    );
  }

  return (
    <div className={disabled ? 'pointer-events-none opacity-60' : ''}>
      <div ref={containerRef} />
      {!ready && <div className="mt-2 text-xs text-gray-500">Loading Google Sign-In…</div>}
    </div>
  );
}
