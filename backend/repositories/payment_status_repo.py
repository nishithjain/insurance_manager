"""Reference-data lookups for the ``payment_statuses`` table."""

from __future__ import annotations

from typing import Optional

import aiosqlite


async def default_payment_status_id(db: aiosqlite.Connection) -> Optional[int]:
    """Return the ``Unknown`` ``payment_status_id``, if seeded."""
    async with db.execute(
        "SELECT payment_status_id FROM payment_statuses WHERE status_name = 'Unknown' LIMIT 1"
    ) as cur:
        row = await cur.fetchone()
    return int(row[0]) if row else None


async def payment_status_id_by_name(
    db: aiosqlite.Connection, name: str
) -> Optional[int]:
    """Look up a ``payment_status_id`` by name; returns ``None`` if not seeded."""
    async with db.execute(
        "SELECT payment_status_id FROM payment_statuses WHERE status_name = ?",
        (name,),
    ) as c:
        row = await c.fetchone()
    return int(row[0]) if row else None
