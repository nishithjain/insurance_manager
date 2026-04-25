"""
Reference-data seeds and the bootstrap-admin step.

Idempotent. Re-running this is harmless because every insert is guarded by
``WHERE NOT EXISTS`` or a uniqueness check.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger(__name__)


# Two-layer master data: ``insurance_categories`` (parent) and ``policy_types``
# (child). Seeded with sensible defaults so the UI dropdowns are populated on
# first run. Existing ``insurance_types`` rows are kept untouched — they back
# the legacy ``policies.insurance_type_id`` FK and stay the source of truth
# for the per-LOB detail tables (motor / health / property).
INSURANCE_CATEGORY_DEFAULTS: tuple[str, ...] = (
    "Motor",
    "Health",
    "Life",
    "Travel",
    "Property",
)

POLICY_TYPE_DEFAULTS: tuple[tuple[str, str], ...] = (
    ("Motor", "Comprehensive"),
    ("Motor", "Third Party"),
    ("Motor", "Own Damage"),
    ("Health", "Individual"),
    ("Health", "Family Floater"),
    ("Health", "Group Policy"),
    ("Life", "Term Plan"),
    ("Life", "Endowment Plan"),
    ("Life", "ULIP"),
    ("Travel", "Domestic Travel"),
    ("Travel", "International Travel"),
    ("Property", "Home Insurance"),
    ("Property", "Commercial Property"),
)


# Canonical labels (uppercase) — keep in sync with frontend paymentStatus.js.
# Used by both the seed step and the legacy → canonical migration.
PAYMENT_STATUS_CANONICAL: tuple[str, ...] = (
    "PENDING",
    "CUSTOMER ONLINE",
    "CUSTOMER CHEQUE",
    "TRANSFER TO SAMRAJ",
    "CASH TO SAMRAJ",
    "CASH TO SANDESH",
    "Paid",
    "Partial",
    "Unknown",
)


_LEGACY_INSURANCE_TYPE_ROWS: tuple[tuple[str, str], ...] = (
    ("Private Car", "Motor"),
    ("Two Wheeler", "Motor"),
    ("Health", "Health"),
    ("Property", "Property"),
)


async def seed_reference_data(db: aiosqlite.Connection) -> None:
    """Populate lookup tables on a fresh database (idempotent)."""
    async with db.execute("SELECT COUNT(*) FROM insurance_types") as cur:
        legacy_count = (await cur.fetchone())[0]
    if legacy_count == 0:
        await db.executemany(
            "INSERT INTO insurance_types (insurance_type_name, category_group) VALUES (?, ?)",
            _LEGACY_INSURANCE_TYPE_ROWS,
        )
    async with db.execute("SELECT COUNT(*) FROM payment_statuses") as cur:
        ps_count = (await cur.fetchone())[0]
    if ps_count == 0:
        for label in PAYMENT_STATUS_CANONICAL:
            await db.execute(
                """
                INSERT INTO payment_statuses (status_name)
                SELECT ? WHERE NOT EXISTS (SELECT 1 FROM payment_statuses WHERE status_name = ?)
                """,
                (label, label),
            )


async def bootstrap_initial_admin(db: aiosqlite.Connection) -> None:
    """
    Seed the very first admin from ``INITIAL_ADMIN_EMAIL`` (+ optional
    ``INITIAL_ADMIN_NAME``) when the auth table has no admins yet.

    This is the only way a brand-new deployment gets its first admin —
    subsequent admins are created through the admin UI by an already-
    logged-in admin. If the env var is unset the function is a no-op and
    the UI will refuse all logins until an operator seeds one manually.
    """
    async with db.execute(
        "SELECT COUNT(*) FROM app_users WHERE role = 'admin' AND is_active = 1"
    ) as cur:
        admin_count = (await cur.fetchone())[0]
    if admin_count > 0:
        return

    email = (os.environ.get("INITIAL_ADMIN_EMAIL") or "").strip().lower()
    if not email:
        logger.warning(
            "No active admin users in app_users and INITIAL_ADMIN_EMAIL is unset. "
            "Google Sign-In will reject every login until an admin is seeded."
        )
        return

    full_name = (
        os.environ.get("INITIAL_ADMIN_NAME") or "Administrator"
    ).strip() or "Administrator"
    now = datetime.now(timezone.utc).isoformat()

    async with db.execute(
        "SELECT id, role, is_active FROM app_users WHERE email = ? COLLATE NOCASE",
        (email,),
    ) as cur:
        existing = await cur.fetchone()
    if existing:
        await db.execute(
            "UPDATE app_users SET role = 'admin', is_active = 1, updated_at = ? WHERE id = ?",
            (now, existing[0]),
        )
        logger.info("Promoted existing app_users row '%s' to active admin.", email)
        return

    await db.execute(
        """INSERT INTO app_users (email, full_name, role, is_active, created_at, updated_at)
           VALUES (?, ?, 'admin', 1, ?, ?)""",
        (email, full_name, now, now),
    )
    logger.info("Seeded initial admin app_user '%s'.", email)


__all__ = [
    "INSURANCE_CATEGORY_DEFAULTS",
    "POLICY_TYPE_DEFAULTS",
    "PAYMENT_STATUS_CANONICAL",
    "seed_reference_data",
    "bootstrap_initial_admin",
]
