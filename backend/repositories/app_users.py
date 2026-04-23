"""
Data access for the ``app_users`` table.

Pure SQL / aiosqlite — no HTTP types, no role-policy decisions, no JWT. Services
consume this; routers never touch it directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import aiosqlite


@dataclass(frozen=True)
class AppUserRow:
    """
    Snapshot of one ``app_users`` row. Immutable so services can hand it to the
    router layer without worrying about mutation.
    """

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str
    created_by: Optional[int]
    last_login_at: Optional[str]


def _row_to_model(row: aiosqlite.Row) -> AppUserRow:
    return AppUserRow(
        id=int(row["id"]),
        email=str(row["email"]),
        full_name=str(row["full_name"]),
        role=str(row["role"]),
        is_active=bool(row["is_active"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        created_by=(int(row["created_by"]) if row["created_by"] is not None else None),
        last_login_at=(str(row["last_login_at"]) if row["last_login_at"] else None),
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AppUserRepository:
    """Thin CRUD wrapper around ``app_users``."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def get_by_id(self, user_id: int) -> Optional[AppUserRow]:
        async with self._db.execute(
            "SELECT * FROM app_users WHERE id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        return _row_to_model(row) if row else None

    async def get_by_email(self, email: str) -> Optional[AppUserRow]:
        async with self._db.execute(
            "SELECT * FROM app_users WHERE email = ? COLLATE NOCASE",
            (email.strip().lower(),),
        ) as cur:
            row = await cur.fetchone()
        return _row_to_model(row) if row else None

    async def list_all(
        self,
        *,
        search: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[AppUserRow]:
        sql = "SELECT * FROM app_users"
        params: list[object] = []
        if search:
            sql += " WHERE email LIKE ? COLLATE NOCASE OR full_name LIKE ? COLLATE NOCASE"
            pattern = f"%{search.strip()}%"
            params.extend([pattern, pattern])
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([max(1, min(limit, 500)), max(0, offset)])
        async with self._db.execute(sql, params) as cur:
            rows = await cur.fetchall()
        return [_row_to_model(r) for r in rows]

    async def create(
        self,
        *,
        email: str,
        full_name: str,
        role: str,
        is_active: bool,
        created_by: Optional[int],
    ) -> AppUserRow:
        now = _utc_now_iso()
        await self._db.execute(
            """INSERT INTO app_users
                   (email, full_name, role, is_active, created_at, updated_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (email.strip().lower(), full_name.strip(), role, 1 if is_active else 0, now, now, created_by),
        )
        await self._db.commit()
        async with self._db.execute("SELECT last_insert_rowid()") as cur:
            new_id = int((await cur.fetchone())[0])
        created = await self.get_by_id(new_id)
        assert created is not None
        return created

    async def update_profile(
        self,
        *,
        user_id: int,
        full_name: Optional[str],
        role: Optional[str],
        is_active: Optional[bool],
    ) -> Optional[AppUserRow]:
        sets: list[str] = []
        params: list[object] = []
        if full_name is not None:
            sets.append("full_name = ?")
            params.append(full_name.strip())
        if role is not None:
            sets.append("role = ?")
            params.append(role)
        if is_active is not None:
            sets.append("is_active = ?")
            params.append(1 if is_active else 0)
        if not sets:
            return await self.get_by_id(user_id)

        sets.append("updated_at = ?")
        params.append(_utc_now_iso())
        params.append(user_id)

        await self._db.execute(
            f"UPDATE app_users SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        await self._db.commit()
        return await self.get_by_id(user_id)

    async def set_last_login(self, user_id: int) -> None:
        now = _utc_now_iso()
        await self._db.execute(
            "UPDATE app_users SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (now, now, user_id),
        )
        await self._db.commit()

    async def delete(self, user_id: int) -> bool:
        """Hard-delete. Prefer :meth:`update_profile` with ``is_active=False``."""
        await self._db.execute("DELETE FROM app_users WHERE id = ?", (user_id,))
        await self._db.commit()
        async with self._db.execute(
            "SELECT changes()"
        ) as cur:
            changes = int((await cur.fetchone())[0])
        return changes > 0

    async def count_active_admins(self) -> int:
        async with self._db.execute(
            "SELECT COUNT(*) FROM app_users WHERE role = 'admin' AND is_active = 1"
        ) as cur:
            return int((await cur.fetchone())[0])
