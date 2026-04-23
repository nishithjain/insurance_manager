"""
Admin use cases for managing ``app_users`` rows.

Enforces business rules that the repository does not (and should not) know about:

- Only valid role vocabulary is accepted.
- Admins cannot accidentally lock themselves out (last active admin is protected).
- Disabled users are disabled by flipping ``is_active`` rather than deletion.
- Duplicate emails surface as a 409-equivalent :class:`ValueError`.
"""

from __future__ import annotations

from typing import Optional

from domain.auth import AppRole, normalize_email
from repositories.app_users import AppUserRepository, AppUserRow


class AppUserServiceError(Exception):
    """Base class for all user-facing service errors."""


class DuplicateEmailError(AppUserServiceError):
    """A row with this email already exists."""


class LastActiveAdminError(AppUserServiceError):
    """Tried to demote/deactivate/delete the final active admin."""


class AppUserService:
    def __init__(self, repo: AppUserRepository) -> None:
        self._repo = repo

    # -- read --

    async def list_users(
        self, *, search: Optional[str], limit: int, offset: int
    ) -> list[AppUserRow]:
        return await self._repo.list_all(search=search, limit=limit, offset=offset)

    async def get_user(self, user_id: int) -> Optional[AppUserRow]:
        return await self._repo.get_by_id(user_id)

    # -- write --

    async def create_user(
        self,
        *,
        email: str,
        full_name: str,
        role: str,
        is_active: bool,
        created_by: Optional[int],
    ) -> AppUserRow:
        canonical_email = normalize_email(email)
        parsed_role = AppRole.parse(role)

        if await self._repo.get_by_email(canonical_email) is not None:
            raise DuplicateEmailError(
                f"A user with email '{canonical_email}' already exists."
            )

        return await self._repo.create(
            email=canonical_email,
            full_name=full_name.strip(),
            role=parsed_role.value,
            is_active=is_active,
            created_by=created_by,
        )

    async def update_user(
        self,
        *,
        user_id: int,
        full_name: Optional[str],
        role: Optional[str],
        is_active: Optional[bool],
    ) -> Optional[AppUserRow]:
        existing = await self._repo.get_by_id(user_id)
        if existing is None:
            return None

        target_role = AppRole.parse(role).value if role is not None else existing.role
        target_active = existing.is_active if is_active is None else is_active

        # Protect the last active admin: deactivating or demoting is not allowed
        # unless another active admin exists.
        losing_admin_privileges = (
            existing.role == AppRole.ADMIN.value
            and existing.is_active
            and (target_role != AppRole.ADMIN.value or not target_active)
        )
        if losing_admin_privileges:
            active_admins = await self._repo.count_active_admins()
            if active_admins <= 1:
                raise LastActiveAdminError(
                    "Cannot demote or deactivate the last active admin. "
                    "Promote another user to admin first."
                )

        return await self._repo.update_profile(
            user_id=user_id,
            full_name=full_name,
            role=target_role if role is not None else None,
            is_active=is_active,
        )

    async def set_status(self, *, user_id: int, is_active: bool) -> Optional[AppUserRow]:
        return await self.update_user(
            user_id=user_id,
            full_name=None,
            role=None,
            is_active=is_active,
        )

    async def delete_user(self, *, user_id: int) -> bool:
        existing = await self._repo.get_by_id(user_id)
        if existing is None:
            return False
        # Symmetric protection with deactivation.
        if existing.role == AppRole.ADMIN.value and existing.is_active:
            active_admins = await self._repo.count_active_admins()
            if active_admins <= 1:
                raise LastActiveAdminError(
                    "Cannot delete the last active admin."
                )
        return await self._repo.delete(user_id)
