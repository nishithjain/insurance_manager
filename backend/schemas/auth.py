"""
HTTP-facing schemas for authentication and admin user management.

``AppUser`` is the response shape returned from every user-facing endpoint;
it intentionally omits fields that only exist for storage bookkeeping.

Note: Pydantic ``BaseModel`` already rejects unknown fields during validation
of request bodies — so a client trying to forge ``id`` / ``created_at`` on a
create payload will be ignored cleanly, not silently accepted.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class AppUser(BaseModel):
    """
    Admin-panel and ``/auth/me`` response shape.

    ``email`` is plain ``str`` on the response side because the stored value
    has already been verified (either by Google Sign-In or by strict
    ``EmailStr`` validation on :class:`AppUserCreate`). Re-validating on read
    would reject legitimate internal-TLD addresses that strict validators
    classify as "special-use".
    """

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str
    created_by: Optional[int] = None
    last_login_at: Optional[str] = None


class AppUserCreate(BaseModel):
    """Admin → ``POST /api/users`` body."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    role: str = Field(description="'admin' or 'user'")
    is_active: bool = True


class AppUserUpdate(BaseModel):
    """Admin → ``PUT /api/users/{id}`` body. All fields optional (partial update)."""

    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    role: Optional[str] = None
    is_active: Optional[bool] = None


class AppUserStatusUpdate(BaseModel):
    """Admin → ``PUT /api/users/{id}/status`` body."""

    is_active: bool


class GoogleLoginRequest(BaseModel):
    """``POST /api/auth/google`` — client trades Google ID token for our JWT."""

    id_token: str = Field(min_length=16)


class DevLoginRequest(BaseModel):
    """
    ``POST /api/auth/dev-login`` — dev-only shortcut to mint a session by email.

    Only honored when the backend has ``ALLOW_DEV_AUTH=true``. Useful for
    emulators / CI where configuring a real Google account is impractical.
    """

    email: str = Field(min_length=3, max_length=320)


class TokenResponse(BaseModel):
    """Successful login response. ``user`` included so the client can skip ``/me``."""

    access_token: str
    token_type: str = "Bearer"
    expires_at: str
    user: AppUser
