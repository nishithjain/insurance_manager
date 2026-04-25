"""
Reference-data helpers for the two-layer insurance taxonomy plus the legacy
``insurance_types`` lookup table that ``policies.insurance_type_id`` still
foreign-keys into.

The new tables (``insurance_categories`` + ``policy_types``) are the canonical
parent/child hierarchy surfaced through the new APIs and the cascading
dropdowns in the web UI. The legacy table is kept around so existing rows
continue to satisfy the FK and so older code paths (CSV exports, statistics,
per-LOB detail tables) keep working — :func:`resolve_legacy_insurance_type_for_category`
is the bridge.
"""

from __future__ import annotations

from typing import Optional

import aiosqlite
from fastapi import HTTPException


async def resolve_insurance_type_id(
    db: aiosqlite.Connection, slug_or_name: str
) -> int:
    """
    Map a manual-form slug (e.g. ``auto``) to an
    ``insurance_types.insurance_type_id``. Falls back to the first Motor type
    if the configured name isn't present.
    """
    from domain.constants import POLICY_SLUG_TO_TYPE_NAME

    name = POLICY_SLUG_TO_TYPE_NAME.get((slug_or_name or "auto").lower(), "Private Car")
    async with db.execute(
        "SELECT insurance_type_id FROM insurance_types WHERE insurance_type_name = ?",
        (name,),
    ) as cur:
        row = await cur.fetchone()
    if row:
        return int(row[0])
    async with db.execute(
        """SELECT insurance_type_id FROM insurance_types
           WHERE category_group = 'Motor' ORDER BY insurance_type_id LIMIT 1"""
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="insurance_types table is empty")
    return int(row[0])


async def get_insurance_category_id_by_name(
    db: aiosqlite.Connection, name: str
) -> Optional[int]:
    """Look up an ``insurance_categories.id`` by name (case-insensitive)."""
    async with db.execute(
        "SELECT id FROM insurance_categories WHERE name = ? COLLATE NOCASE LIMIT 1",
        (name,),
    ) as cur:
        row = await cur.fetchone()
    return int(row[0]) if row else None


async def get_policy_type_with_category(
    db: aiosqlite.Connection, policy_type_id: int
) -> Optional[dict]:
    """Return the ``policy_types`` row joined with its parent category, or ``None``."""
    async with db.execute(
        """SELECT pt.id AS id, pt.name AS name, pt.is_active AS is_active,
                  pt.insurance_category_id AS insurance_category_id,
                  ic.name AS insurance_category_name
           FROM policy_types pt
           JOIN insurance_categories ic ON ic.id = pt.insurance_category_id
           WHERE pt.id = ?""",
        (policy_type_id,),
    ) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def resolve_legacy_insurance_type_for_category(
    db: aiosqlite.Connection, category_name: str
) -> int:
    """
    Pick a legacy ``insurance_types`` row to satisfy the existing
    ``policies.insurance_type_id`` NOT NULL FK when a policy is created
    using the new taxonomy.

    Strategy: prefer an exact ``category_group`` match; if missing (e.g.
    Life, Travel) auto-create a single legacy row with
    ``insurance_type_name = category_group = <category_name>``. This keeps
    old code paths (CSV export, statistics, motor/health/property detail
    tables) functional while letting the new categories flow through
    unmodified.
    """
    cat = (category_name or "").strip()
    if not cat:
        async with db.execute(
            "SELECT insurance_type_id FROM insurance_types ORDER BY insurance_type_id LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="insurance_types is empty")
        return int(row[0])

    async with db.execute(
        """SELECT insurance_type_id FROM insurance_types
           WHERE category_group = ? COLLATE NOCASE
           ORDER BY insurance_type_id LIMIT 1""",
        (cat,),
    ) as cur:
        row = await cur.fetchone()
    if row:
        return int(row[0])

    # Auto-create a placeholder legacy row for new categories (Life/Travel).
    # Use INSERT OR IGNORE in case an unrelated row with the same name already
    # exists; fall back to a name-based SELECT either way.
    await db.execute(
        """INSERT OR IGNORE INTO insurance_types (insurance_type_name, category_group)
           VALUES (?, ?)""",
        (cat, cat),
    )
    async with db.execute(
        """SELECT insurance_type_id FROM insurance_types
           WHERE insurance_type_name = ? COLLATE NOCASE
           ORDER BY insurance_type_id LIMIT 1""",
        (cat,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resolve legacy insurance_type for category '{cat}'",
        )
    return int(row[0])
