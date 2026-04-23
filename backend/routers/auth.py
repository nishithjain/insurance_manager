"""
Authentication endpoints.

These are the **only** endpoints under ``/api`` that must be reachable without
a valid principal, so we register them on a dedicated ``APIRouter`` and leave
the role/JWT guard off here. Every other router in the app receives the
``get_current_principal`` dependency via the parent include.
"""

from __future__ import annotations

import logging
import os

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status

from deps import get_current_principal, get_db
from domain.security import AuthConfigError
from repositories.app_users import AppUserRepository
from schemas import AppUser, DevLoginRequest, GoogleLoginRequest, TokenResponse
from services.auth_service import AuthService, LoginError


def _dev_auth_enabled() -> bool:
    """``ALLOW_DEV_AUTH=true`` is the single switch for every dev-only endpoint."""
    return os.getenv("ALLOW_DEV_AUTH", "false").strip().lower() in {"1", "true", "yes", "on"}

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)


def _to_appuser_dto(row) -> AppUser:
    """Translate a repository row into the response schema."""
    return AppUser(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        role=row.role,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        last_login_at=row.last_login_at,
    )


@router.post("/auth/google", response_model=TokenResponse)
async def login_with_google(
    payload: GoogleLoginRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> TokenResponse:
    """
    Exchange a Google ID token for a backend JWT.

    The backend verifies the Google token against the configured
    ``GOOGLE_CLIENT_ID``, then requires the resulting email to match an active
    row in ``app_users``. Unknown or disabled emails get a generic 401.
    """
    service = AuthService(AppUserRepository(db))
    try:
        result = await service.login_with_google(payload.id_token)
    except AuthConfigError as exc:
        logger.error("Login rejected due to auth misconfiguration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured on this server.",
        ) from exc
    except LoginError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return TokenResponse(
        access_token=result.access_token,
        token_type="Bearer",
        expires_at=result.expires_at.isoformat(),
        user=_to_appuser_dto(result.user),
    )


@router.post("/auth/dev-login", response_model=TokenResponse)
async def login_dev(
    payload: DevLoginRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> TokenResponse:
    """
    Dev-only login: mint a session for an existing, active user by email.

    Intentionally **never** available unless the server sets
    ``ALLOW_DEV_AUTH=true``. In production the endpoint returns 404 so its
    existence is not even advertised.
    """
    if not _dev_auth_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    service = AuthService(AppUserRepository(db))
    try:
        result = await service.login_dev(payload.email)
    except LoginError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    logger.warning("Dev login used for %s. Disable ALLOW_DEV_AUTH in production.", result.user.email)
    return TokenResponse(
        access_token=result.access_token,
        token_type="Bearer",
        expires_at=result.expires_at.isoformat(),
        user=_to_appuser_dto(result.user),
    )


@router.get("/auth/me", response_model=AppUser)
async def get_me(
    principal=Depends(get_current_principal),
) -> AppUser:
    """Return the currently logged-in user based on the Bearer token."""
    return _to_appuser_dto(principal)


@router.post("/auth/logout")
async def logout() -> dict[str, str]:
    """
    Stateless logout.

    We issue short-lived JWTs and do not persist a server-side session table,
    so a logout on the server is effectively a no-op — the client is expected
    to drop its stored token. This endpoint exists so client code can reason
    about logout uniformly and so we can plug in a revocation list later
    without changing the wire contract.
    """
    return {"message": "Logged out."}
