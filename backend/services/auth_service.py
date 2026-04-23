"""
Login use case: turn a Google ID token into a backend JWT.

Flow:
    1. Verify the Google ID token's signature and audience (domain/security).
    2. Look up the verified email in ``app_users``.
    3. Reject unknown users (allow-list enforcement) and inactive users.
    4. Stamp ``last_login_at`` and issue a short-lived backend JWT.

The router is a thin wrapper: it converts domain/service errors into HTTP status
codes and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.auth import normalize_email
from domain.security import (
    GoogleTokenError,
    create_access_token,
    verify_google_id_token,
)
from repositories.app_users import AppUserRepository, AppUserRow


class LoginError(Exception):
    """Raised with a user-safe message on any login failure."""


@dataclass(frozen=True)
class LoginResult:
    """Successful login outcome."""

    user: AppUserRow
    access_token: str
    expires_at: datetime


class AuthService:
    """Verify Google identities and issue backend sessions."""

    def __init__(self, repo: AppUserRepository) -> None:
        self._repo = repo

    async def login_with_google(self, id_token: str) -> LoginResult:
        try:
            identity = verify_google_id_token(id_token)
        except GoogleTokenError as exc:
            raise LoginError(str(exc)) from exc

        existing = await self._repo.get_by_email(identity.email)
        if existing is None:
            # Allow-list miss. Message is intentionally vague: we don't want to
            # leak whether an email is provisioned to a casual prober.
            raise LoginError(
                "Your Google account is not authorized to access this application. "
                "Ask an administrator to add your Gmail ID."
            )
        if not existing.is_active:
            raise LoginError("Your account has been disabled. Contact an administrator.")

        token, expires_at = create_access_token(
            user_id=existing.id,
            email=existing.email,
            role=existing.role,
        )
        await self._repo.set_last_login(existing.id)
        return LoginResult(user=existing, access_token=token, expires_at=expires_at)

    async def login_dev(self, email: str) -> LoginResult:
        """
        Dev/QA shortcut: mint a session for an existing, active app_user by email.

        Skips Google verification entirely. The allow-list (must exist in
        ``app_users``) and active check are still enforced, so a disabled user
        stays disabled. The router guards this method behind ``ALLOW_DEV_AUTH``
        so it never runs in production.
        """
        normalized = normalize_email(email)
        if not normalized:
            raise LoginError("Email is required.")
        existing = await self._repo.get_by_email(normalized)
        if existing is None:
            raise LoginError(
                "This email is not provisioned. Ask an administrator to add it."
            )
        if not existing.is_active:
            raise LoginError("Your account has been disabled. Contact an administrator.")

        token, expires_at = create_access_token(
            user_id=existing.id,
            email=existing.email,
            role=existing.role,
        )
        await self._repo.set_last_login(existing.id)
        return LoginResult(user=existing, access_token=token, expires_at=expires_at)
