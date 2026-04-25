"""
CRUD helpers for the admin "Insurance Master" page.

This module owns every write that comes from the new
``/api/admin/insurance-types`` and ``/api/admin/policy-types`` endpoints.
The existing :mod:`repositories.insurance_type_repo` keeps doing what it has
always done (resolve legacy FKs for policy creation); the helpers here are
strictly about managing the master tables themselves.

Design choices worth knowing:

* **Soft delete when in use.** A row is hard-deleted only when no policies
  reference it; otherwise we flip ``is_active = 0`` so historic policies
  keep their human-readable category/type label.
* **Case-insensitive uniqueness.** ``insurance_categories`` already enforces
  it via the column collation; ``policy_types`` has a composite unique
  constraint, but we still pre-check at the application layer to surface
  a friendly 409 instead of the raw SQLite IntegrityError.
* **Usage definition.**
    * Insurance Type is "in use" when any policy points (via
      ``policies.policy_type_id``) at one of its child policy types, OR when
      any legacy ``insurance_types`` row with a matching category_group is
      referenced by a policy. The second branch keeps the single source of
      truth honest while the legacy table still backs the FK.
    * Policy Type is "in use" purely via ``policies.policy_type_id``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import aiosqlite


# --------------------------------------------------------------------------- #
# Domain errors                                                                #
# --------------------------------------------------------------------------- #


class InsuranceMasterError(Exception):
    """Service-level error with an HTTP status hint for the router layer."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Insurance Type (parent) — ``insurance_categories`` table                     #
# --------------------------------------------------------------------------- #


_INSURANCE_TYPE_SELECT = """
    SELECT
        ic.id                 AS id,
        ic.name               AS name,
        ic.description        AS description,
        ic.is_active          AS is_active,
        ic.created_at         AS created_at,
        ic.updated_at         AS updated_at,
        (SELECT COUNT(*) FROM policy_types pt
            WHERE pt.insurance_category_id = ic.id) AS policy_type_count,
        EXISTS (
            SELECT 1
              FROM policies p
              JOIN policy_types pt ON pt.id = p.policy_type_id
             WHERE pt.insurance_category_id = ic.id
            UNION ALL
            SELECT 1
              FROM policies p
              JOIN insurance_types it ON it.insurance_type_id = p.insurance_type_id
             WHERE it.category_group = ic.name COLLATE NOCASE
        ) AS in_use
    FROM insurance_categories ic
"""


async def list_insurance_types(
    db: aiosqlite.Connection,
    *,
    include_inactive: bool = True,
) -> list[dict]:
    """List every insurance category with usage counters."""
    where = "" if include_inactive else "WHERE ic.is_active = 1"
    sql = f"{_INSURANCE_TYPE_SELECT} {where} ORDER BY ic.name COLLATE NOCASE"
    async with db.execute(sql) as cur:
        rows = await cur.fetchall()
    return [_row_to_insurance_type(r) for r in rows]


async def get_insurance_type(
    db: aiosqlite.Connection, type_id: int
) -> Optional[dict]:
    sql = f"{_INSURANCE_TYPE_SELECT} WHERE ic.id = ?"
    async with db.execute(sql, (type_id,)) as cur:
        row = await cur.fetchone()
    return _row_to_insurance_type(row) if row else None


async def find_insurance_type_by_name(
    db: aiosqlite.Connection, name: str
) -> Optional[int]:
    async with db.execute(
        "SELECT id FROM insurance_categories WHERE name = ? COLLATE NOCASE LIMIT 1",
        (name,),
    ) as cur:
        row = await cur.fetchone()
    return int(row[0]) if row else None


async def create_insurance_type(
    db: aiosqlite.Connection,
    *,
    name: str,
    description: Optional[str],
    is_active: bool,
) -> dict:
    """Insert a new ``insurance_categories`` row, raising 409 on duplicate name."""
    if await find_insurance_type_by_name(db, name) is not None:
        raise InsuranceMasterError(
            409, f"An Insurance Type named '{name}' already exists."
        )
    now = _now()
    cur = await db.execute(
        """INSERT INTO insurance_categories
                (name, description, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)""",
        (name, description, 1 if is_active else 0, now, now),
    )
    new_id = cur.lastrowid
    await db.commit()
    row = await get_insurance_type(db, int(new_id))
    assert row is not None
    return row


async def update_insurance_type(
    db: aiosqlite.Connection,
    *,
    type_id: int,
    name: Optional[str],
    description: Optional[str],
    is_active: Optional[bool],
    description_was_set: bool,
) -> Optional[dict]:
    """
    Patch any subset of fields. Returns ``None`` if the row doesn't exist.
    ``description_was_set`` tells us whether the caller meant to clear the
    description (sent ``None`` explicitly) or just omitted the field.
    """
    existing = await get_insurance_type(db, type_id)
    if existing is None:
        return None

    if name is not None and name.lower() != existing["name"].lower():
        dup = await find_insurance_type_by_name(db, name)
        if dup is not None and dup != type_id:
            raise InsuranceMasterError(
                409, f"An Insurance Type named '{name}' already exists."
            )

    sets: list[str] = []
    params: list = []
    if name is not None:
        sets.append("name = ?")
        params.append(name)
    if description_was_set:
        sets.append("description = ?")
        params.append(description)
    if is_active is not None:
        sets.append("is_active = ?")
        params.append(1 if is_active else 0)

    if not sets:
        return existing

    sets.append("updated_at = ?")
    params.append(_now())
    params.append(type_id)

    await db.execute(
        f"UPDATE insurance_categories SET {', '.join(sets)} WHERE id = ?",
        tuple(params),
    )
    await db.commit()
    return await get_insurance_type(db, type_id)


async def delete_insurance_type(
    db: aiosqlite.Connection, type_id: int
) -> tuple[str, Optional[dict]]:
    """
    Hard-delete when unused; otherwise flip ``is_active = 0`` and return the
    updated row plus a status string ("deleted" | "deactivated" | "not_found").

    Cascades to ``policy_types`` via the schema FK, which is desirable: an
    unused parent has no policies referencing any of its (also unused) children.
    """
    existing = await get_insurance_type(db, type_id)
    if existing is None:
        return "not_found", None

    if not existing["in_use"]:
        await db.execute(
            "DELETE FROM insurance_categories WHERE id = ?", (type_id,)
        )
        await db.commit()
        return "deleted", None

    await db.execute(
        "UPDATE insurance_categories SET is_active = 0, updated_at = ? WHERE id = ?",
        (_now(), type_id),
    )
    await db.commit()
    return "deactivated", await get_insurance_type(db, type_id)


def _row_to_insurance_type(row) -> dict:
    return {
        "id": int(row["id"]),
        "name": str(row["name"]),
        "description": row["description"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "policy_type_count": int(row["policy_type_count"] or 0),
        "in_use": bool(row["in_use"]),
    }


# --------------------------------------------------------------------------- #
# Policy Type (child) — ``policy_types`` table                                 #
# --------------------------------------------------------------------------- #


_POLICY_TYPE_SELECT = """
    SELECT
        pt.id                       AS id,
        pt.insurance_category_id    AS insurance_type_id,
        ic.name                     AS insurance_type_name,
        pt.name                     AS name,
        pt.description              AS description,
        pt.is_active                AS is_active,
        pt.created_at               AS created_at,
        pt.updated_at               AS updated_at,
        EXISTS (SELECT 1 FROM policies p WHERE p.policy_type_id = pt.id) AS in_use
    FROM policy_types pt
    JOIN insurance_categories ic ON ic.id = pt.insurance_category_id
"""


async def list_policy_types(
    db: aiosqlite.Connection,
    *,
    insurance_type_id: Optional[int] = None,
    include_inactive: bool = True,
) -> list[dict]:
    clauses: list[str] = []
    params: list = []
    if insurance_type_id is not None:
        clauses.append("pt.insurance_category_id = ?")
        params.append(insurance_type_id)
    if not include_inactive:
        clauses.append("pt.is_active = 1")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        f"{_POLICY_TYPE_SELECT} {where} "
        "ORDER BY ic.name COLLATE NOCASE, pt.name COLLATE NOCASE"
    )
    async with db.execute(sql, tuple(params)) as cur:
        rows = await cur.fetchall()
    return [_row_to_policy_type(r) for r in rows]


async def get_policy_type(
    db: aiosqlite.Connection, policy_type_id: int
) -> Optional[dict]:
    sql = f"{_POLICY_TYPE_SELECT} WHERE pt.id = ?"
    async with db.execute(sql, (policy_type_id,)) as cur:
        row = await cur.fetchone()
    return _row_to_policy_type(row) if row else None


async def _find_policy_type_in_parent(
    db: aiosqlite.Connection, *, parent_id: int, name: str
) -> Optional[int]:
    async with db.execute(
        """SELECT id FROM policy_types
           WHERE insurance_category_id = ? AND name = ? COLLATE NOCASE
           LIMIT 1""",
        (parent_id, name),
    ) as cur:
        row = await cur.fetchone()
    return int(row[0]) if row else None


async def _parent_exists(db: aiosqlite.Connection, parent_id: int) -> bool:
    async with db.execute(
        "SELECT 1 FROM insurance_categories WHERE id = ? LIMIT 1", (parent_id,)
    ) as cur:
        return (await cur.fetchone()) is not None


async def create_policy_type(
    db: aiosqlite.Connection,
    *,
    insurance_type_id: int,
    name: str,
    description: Optional[str],
    is_active: bool,
) -> dict:
    if not await _parent_exists(db, insurance_type_id):
        raise InsuranceMasterError(
            400, "Selected Insurance Type does not exist."
        )
    if (
        await _find_policy_type_in_parent(
            db, parent_id=insurance_type_id, name=name
        )
        is not None
    ):
        raise InsuranceMasterError(
            409,
            f"A Policy Type named '{name}' already exists under this Insurance Type.",
        )
    now = _now()
    cur = await db.execute(
        """INSERT INTO policy_types
                (insurance_category_id, name, description,
                 is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (insurance_type_id, name, description, 1 if is_active else 0, now, now),
    )
    new_id = cur.lastrowid
    await db.commit()
    row = await get_policy_type(db, int(new_id))
    assert row is not None
    return row


async def update_policy_type(
    db: aiosqlite.Connection,
    *,
    policy_type_id: int,
    insurance_type_id: Optional[int],
    name: Optional[str],
    description: Optional[str],
    is_active: Optional[bool],
    description_was_set: bool,
) -> Optional[dict]:
    existing = await get_policy_type(db, policy_type_id)
    if existing is None:
        return None

    target_parent = (
        insurance_type_id
        if insurance_type_id is not None
        else int(existing["insurance_type_id"])
    )
    target_name = name if name is not None else str(existing["name"])

    if insurance_type_id is not None and not await _parent_exists(
        db, target_parent
    ):
        raise InsuranceMasterError(
            400, "Selected Insurance Type does not exist."
        )

    parent_changed = target_parent != int(existing["insurance_type_id"])
    name_changed = target_name.lower() != str(existing["name"]).lower()
    if parent_changed or name_changed:
        dup = await _find_policy_type_in_parent(
            db, parent_id=target_parent, name=target_name
        )
        if dup is not None and dup != policy_type_id:
            raise InsuranceMasterError(
                409,
                f"A Policy Type named '{target_name}' already exists "
                "under this Insurance Type.",
            )

    sets: list[str] = []
    params: list = []
    if insurance_type_id is not None:
        sets.append("insurance_category_id = ?")
        params.append(insurance_type_id)
    if name is not None:
        sets.append("name = ?")
        params.append(name)
    if description_was_set:
        sets.append("description = ?")
        params.append(description)
    if is_active is not None:
        sets.append("is_active = ?")
        params.append(1 if is_active else 0)

    if not sets:
        return existing

    sets.append("updated_at = ?")
    params.append(_now())
    params.append(policy_type_id)

    await db.execute(
        f"UPDATE policy_types SET {', '.join(sets)} WHERE id = ?",
        tuple(params),
    )
    await db.commit()
    return await get_policy_type(db, policy_type_id)


async def delete_policy_type(
    db: aiosqlite.Connection, policy_type_id: int
) -> tuple[str, Optional[dict]]:
    existing = await get_policy_type(db, policy_type_id)
    if existing is None:
        return "not_found", None

    if not existing["in_use"]:
        await db.execute("DELETE FROM policy_types WHERE id = ?", (policy_type_id,))
        await db.commit()
        return "deleted", None

    await db.execute(
        "UPDATE policy_types SET is_active = 0, updated_at = ? WHERE id = ?",
        (_now(), policy_type_id),
    )
    await db.commit()
    return "deactivated", await get_policy_type(db, policy_type_id)


def _row_to_policy_type(row) -> dict:
    return {
        "id": int(row["id"]),
        "insurance_type_id": int(row["insurance_type_id"]),
        "insurance_type_name": str(row["insurance_type_name"]),
        "name": str(row["name"]),
        "description": row["description"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "in_use": bool(row["in_use"]),
    }


__all__ = [
    "InsuranceMasterError",
    "create_insurance_type",
    "create_policy_type",
    "delete_insurance_type",
    "delete_policy_type",
    "find_insurance_type_by_name",
    "get_insurance_type",
    "get_policy_type",
    "list_insurance_types",
    "list_policy_types",
    "update_insurance_type",
    "update_policy_type",
]
