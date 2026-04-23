"""
Security primitives: JWT issuance/verification and Google ID-token verification.

Isolates third-party crypto concerns behind small, focused functions so the rest
of the codebase never has to think about ``jwt.decode`` keyword arguments or
Google's transport-requests plumbing.

Configuration (all via environment):
    AUTH_JWT_SECRET        Required in production. In development a deterministic
                           fallback is used so the app still boots — but a clear
                           warning is logged exactly once.
    AUTH_JWT_ALGORITHM     Defaults to HS256.
    AUTH_JWT_LIFETIME_MIN  Access-token lifetime in minutes. Defaults to 720 (12h).
    GOOGLE_CLIENT_ID       OAuth 2.0 Web Client ID used to issue ID tokens. The
                           same client ID must be used by every front-end that
                           authenticates against this backend (web + android).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Final

import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token


logger = logging.getLogger(__name__)


_DEFAULT_ALGORITHM: Final[str] = "HS256"
_DEFAULT_LIFETIME_MINUTES: Final[int] = 720  # 12h

_dev_secret_warned = False


class AuthConfigError(RuntimeError):
    """Raised when a required auth environment variable is missing."""


class TokenError(Exception):
    """Raised when a JWT we issued fails to verify."""


class GoogleTokenError(Exception):
    """Raised when a Google ID token fails to verify."""


@dataclass(frozen=True)
class GoogleIdentity:
    """Minimal view of a verified Google ID token."""

    email: str
    email_verified: bool
    name: str | None
    picture: str | None
    sub: str


def _jwt_secret() -> str:
    """Fetch the signing secret; warn once if the dev fallback is active."""
    secret = os.environ.get("AUTH_JWT_SECRET")
    if secret:
        return secret

    global _dev_secret_warned
    if not _dev_secret_warned:
        logger.warning(
            "AUTH_JWT_SECRET is not set — falling back to a development-only default. "
            "Set AUTH_JWT_SECRET to a long random string before deploying."
        )
        _dev_secret_warned = True
    return "dev-only-change-me-insurance-app-jwt-secret"


def _jwt_algorithm() -> str:
    return os.environ.get("AUTH_JWT_ALGORITHM", _DEFAULT_ALGORITHM)


def _jwt_lifetime() -> timedelta:
    raw = os.environ.get("AUTH_JWT_LIFETIME_MIN")
    try:
        minutes = int(raw) if raw else _DEFAULT_LIFETIME_MINUTES
    except ValueError:
        minutes = _DEFAULT_LIFETIME_MINUTES
    return timedelta(minutes=max(minutes, 1))


# --------------------------------------------------------------------------- #
# Backend JWT (issued by us, consumed by us)                                  #
# --------------------------------------------------------------------------- #


def create_access_token(
    *,
    user_id: int,
    email: str,
    role: str,
    extra: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    """Issue a short-lived access token. Returns (token, expiry_utc)."""
    now = datetime.now(timezone.utc)
    expires_at = now + _jwt_lifetime()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": "insurance-backend",
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify + parse one of our own JWTs. Raises ``TokenError`` on failure."""
    try:
        return jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[_jwt_algorithm()],
            options={"require": ["exp", "sub", "iat"]},
            issuer="insurance-backend",
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Session expired. Please sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid session token.") from exc


# --------------------------------------------------------------------------- #
# Google ID token verification                                                #
# --------------------------------------------------------------------------- #


def _google_client_id() -> str:
    client_id = (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()
    if not client_id:
        raise AuthConfigError(
            "GOOGLE_CLIENT_ID is not set. Configure the OAuth 2.0 Web Client ID "
            "in the backend environment before accepting Google logins."
        )
    return client_id


def verify_google_id_token(raw_token: str) -> GoogleIdentity:
    """
    Verify a Google-issued ID token against the configured client ID.

    This wraps ``google.oauth2.id_token.verify_oauth2_token`` with one extra
    business rule: the email must be verified by Google. An unverified email
    means someone signed up with an unconfirmed Gmail; we reject that here
    rather than in every router.
    """
    if not raw_token or not isinstance(raw_token, str):
        raise GoogleTokenError("Google ID token is required.")

    try:
        payload = google_id_token.verify_oauth2_token(
            raw_token,
            google_requests.Request(),
            _google_client_id(),
        )
    except ValueError as exc:
        raise GoogleTokenError(f"Google ID token rejected: {exc}") from exc

    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise GoogleTokenError("Google ID token does not carry an email address.")
    if not payload.get("email_verified", False):
        raise GoogleTokenError("Google says this email is not verified.")

    return GoogleIdentity(
        email=email,
        email_verified=True,
        name=payload.get("name"),
        picture=payload.get("picture"),
        sub=str(payload.get("sub") or ""),
    )
