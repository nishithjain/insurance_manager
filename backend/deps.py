"""
FastAPI dependencies: DB connection, data-owner user, and the authenticated
principal (app_users row) with a role guard.

- ``get_db`` — one aiosqlite connection per request, guaranteed close.
- ``get_current_user`` — single-tenant data-owner row in ``users`` (customers
  and policies FK here). Kept for backward compatibility with existing routers.
- ``get_current_principal`` — authenticated human (row in ``app_users``).
  Enforces a valid backend JWT and that the user is still active.
- ``require_admin`` — wraps ``get_current_principal`` with a role check.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

import aiosqlite
from fastapi import Depends, HTTPException, Request, status

from database import get_db as _open_db
from domain.auth import AppRole
from domain.security import TokenError, decode_access_token
from repositories.app_users import AppUserRepository, AppUserRow
from schemas import User


# Single-tenant app: all data scoped to one default user row.
DEFAULT_USER_ID = "user_dev_local"
DEFAULT_USER_EMAIL = "dev@local.insurance"
DEFAULT_USER_NAME = "Default User"


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Yield a DB connection scoped to the request, guaranteeing close."""
    db = await _open_db()
    try:
        yield db
    finally:
        await db.close()


async def get_current_user(
    db: aiosqlite.Connection = Depends(get_db),
) -> User:
    """
    Resolve (or create-on-first-use) the single-tenant default data-owner user.

    Kept deliberately distinct from ``get_current_principal``: this is the
    record whose ``user_id`` every customer/policy row FKs into. Even when
    multiple humans (admin + user) are logged in, all data is scoped to this
    single owner, which matches the current product shape.
    """
    async with db.execute(
        "SELECT * FROM users WHERE user_id = ?", (DEFAULT_USER_ID,)
    ) as cursor:
        row = await cursor.fetchone()
    if row:
        return User(**dict(row))

    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO users (user_id, email, name, picture, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (DEFAULT_USER_ID, DEFAULT_USER_EMAIL, DEFAULT_USER_NAME, None, now),
    )
    await db.commit()
    async with db.execute(
        "SELECT * FROM users WHERE user_id = ?", (DEFAULT_USER_ID,)
    ) as cursor:
        row = await cursor.fetchone()
    return User(**dict(row))


# --------------------------------------------------------------------------- #
# Authentication (app_users)                                                  #
# --------------------------------------------------------------------------- #


def _extract_bearer_token(request: Request) -> str:
    """Pull a Bearer token out of the Authorization header or raise 401."""
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


async def get_current_principal(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
) -> AppUserRow:
    """
    Decode the JWT from ``Authorization: Bearer``, load the matching app_users
    row, and verify it is still active. Raises 401 on any failure so the client
    can redirect to login without guessing.
    """
    token = _extract_bearer_token(request)
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await AppUserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session no longer valid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled.",
        )
    return user


async def require_admin(
    principal: AppUserRow = Depends(get_current_principal),
) -> AppUserRow:
    """Deny non-admins. Use this on admin-only endpoints."""
    if principal.role != AppRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required.",
        )
    return principal
