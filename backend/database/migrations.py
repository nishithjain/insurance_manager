"""
Best-effort, idempotent migrations applied at startup.

Each ``_migrate_*`` function adds columns / seed rows / normalizations that a
freshly-issued ``CREATE TABLE IF NOT EXISTS`` cannot express on existing DBs.
They are deliberately safe to re-run because they all use
``PRAGMA table_info`` and ``WHERE NOT EXISTS`` guards.
"""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite

from .seed import (
    INSURANCE_CATEGORY_DEFAULTS,
    PAYMENT_STATUS_CANONICAL,
    POLICY_TYPE_DEFAULTS,
    bootstrap_initial_admin,
)


async def apply_migrations(db: aiosqlite.Connection) -> None:
    """Run every migration in dependency order. Safe to call multiple times."""
    await _migrate_sync_info_columns(db)
    await _migrate_statement_policy_lines_columns(db)
    await _migrate_policy_contact_columns(db)
    await _migrate_policy_renewal_resolution_columns(db)
    await _migrate_app_settings_table(db)
    await _migrate_policy_payment_columns(db)
    await _migrate_payment_status_vocabulary(db)
    await _migrate_insurance_taxonomy(db)
    await _migrate_taxonomy_description_columns(db)
    await bootstrap_initial_admin(db)


async def _migrate_taxonomy_description_columns(db: aiosqlite.Connection) -> None:
    """
    Add ``description`` to ``insurance_categories`` and ``policy_types`` for
    the admin "Insurance Master" UI. Both columns are nullable text; existing
    rows are unaffected.
    """
    async with db.execute("PRAGMA table_info(insurance_categories)") as cursor:
        cat_cols = {r[1] for r in await cursor.fetchall()}
    if "description" not in cat_cols:
        await db.execute(
            "ALTER TABLE insurance_categories ADD COLUMN description TEXT"
        )

    async with db.execute("PRAGMA table_info(policy_types)") as cursor:
        pt_cols = {r[1] for r in await cursor.fetchall()}
    if "description" not in pt_cols:
        await db.execute("ALTER TABLE policy_types ADD COLUMN description TEXT")


async def _migrate_insurance_taxonomy(db: aiosqlite.Connection) -> None:
    """
    Add ``policies.policy_type_id`` and seed the new master tables.

    Existing policy rows are left with ``policy_type_id = NULL`` because the
    variant cannot be inferred from the legacy ``insurance_types`` rows
    (which stored coverage-shape labels like "Private Car", not variants
    like "Comprehensive").
    """
    async with db.execute("PRAGMA table_info(policies)") as cursor:
        names = {r[1] for r in await cursor.fetchall()}
    if "policy_type_id" not in names:
        await db.execute("ALTER TABLE policies ADD COLUMN policy_type_id INTEGER")
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_policies_policy_type_id "
            "ON policies(policy_type_id)"
        )

    now = datetime.now(timezone.utc).isoformat()
    for name in INSURANCE_CATEGORY_DEFAULTS:
        await db.execute(
            """INSERT INTO insurance_categories (name, is_active, created_at, updated_at)
               SELECT ?, 1, ?, ?
               WHERE NOT EXISTS (
                 SELECT 1 FROM insurance_categories WHERE name = ? COLLATE NOCASE
               )""",
            (name, now, now, name),
        )

    async with db.execute("SELECT id, name FROM insurance_categories") as cur:
        cat_rows = await cur.fetchall()
    cat_id_by_name = {str(r["name"]).strip().lower(): int(r["id"]) for r in cat_rows}

    for category, ptype in POLICY_TYPE_DEFAULTS:
        cat_id = cat_id_by_name.get(category.lower())
        if cat_id is None:
            continue
        await db.execute(
            """INSERT INTO policy_types
                 (insurance_category_id, name, is_active, created_at, updated_at)
               SELECT ?, ?, 1, ?, ?
               WHERE NOT EXISTS (
                 SELECT 1 FROM policy_types
                 WHERE insurance_category_id = ? AND name = ? COLLATE NOCASE
               )""",
            (cat_id, ptype, now, now, cat_id, ptype),
        )


async def _migrate_app_settings_table(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


async def _migrate_policy_payment_columns(db: aiosqlite.Connection) -> None:
    async with db.execute("PRAGMA table_info(policies)") as cursor:
        names = {r[1] for r in await cursor.fetchall()}
    if "payment_note" not in names:
        await db.execute("ALTER TABLE policies ADD COLUMN payment_note TEXT")
    if "payment_updated_at" not in names:
        await db.execute("ALTER TABLE policies ADD COLUMN payment_updated_at TEXT")


async def _migrate_payment_status_vocabulary(db: aiosqlite.Connection) -> None:
    """Ensure lookup rows exist; normalize legacy 'Pending' → 'PENDING'."""
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='payment_statuses'"
    ) as cur:
        if not await cur.fetchone():
            return
    for label in PAYMENT_STATUS_CANONICAL:
        await db.execute(
            """
            INSERT INTO payment_statuses (status_name)
            SELECT ? WHERE NOT EXISTS (
                SELECT 1 FROM payment_statuses WHERE status_name = ?
            )
            """,
            (label, label),
        )
    async with db.execute(
        "SELECT payment_status_id FROM payment_statuses WHERE status_name = 'Pending' LIMIT 1"
    ) as cur:
        old_row = await cur.fetchone()
    async with db.execute(
        "SELECT payment_status_id FROM payment_statuses WHERE status_name = 'PENDING' LIMIT 1"
    ) as cur:
        new_row = await cur.fetchone()
    if old_row and new_row and old_row[0] != new_row[0]:
        old_id, new_id = old_row[0], new_row[0]
        await db.execute(
            "UPDATE policies SET payment_status_id = ? WHERE payment_status_id = ?",
            (new_id, old_id),
        )
        await db.execute(
            "DELETE FROM payment_statuses WHERE payment_status_id = ?", (old_id,)
        )
    elif old_row and not new_row:
        await db.execute(
            "UPDATE payment_statuses SET status_name = 'PENDING' WHERE status_name = 'Pending'"
        )


async def _migrate_policy_renewal_resolution_columns(db: aiosqlite.Connection) -> None:
    async with db.execute("PRAGMA table_info(policies)") as cursor:
        names = {r[1] for r in await cursor.fetchall()}
    if "renewal_status" not in names:
        await db.execute(
            "ALTER TABLE policies ADD COLUMN renewal_status TEXT NOT NULL DEFAULT 'Open'"
        )
    if "renewal_resolution_note" not in names:
        await db.execute("ALTER TABLE policies ADD COLUMN renewal_resolution_note TEXT")
    if "renewal_resolved_at" not in names:
        await db.execute("ALTER TABLE policies ADD COLUMN renewal_resolved_at TEXT")
    if "renewal_resolved_by" not in names:
        await db.execute("ALTER TABLE policies ADD COLUMN renewal_resolved_by TEXT")


async def _migrate_policy_contact_columns(db: aiosqlite.Connection) -> None:
    async with db.execute("PRAGMA table_info(policies)") as cursor:
        names = {r[1] for r in await cursor.fetchall()}
    if "last_contacted_at" not in names:
        await db.execute("ALTER TABLE policies ADD COLUMN last_contacted_at TEXT")
    if "contact_status" not in names:
        await db.execute(
            "ALTER TABLE policies ADD COLUMN contact_status TEXT NOT NULL DEFAULT 'Not Contacted'"
        )
    if "follow_up_date" not in names:
        await db.execute("ALTER TABLE policies ADD COLUMN follow_up_date TEXT")


async def _migrate_sync_info_columns(db: aiosqlite.Connection) -> None:
    async with db.execute("PRAGMA table_info(sync_info)") as cursor:
        rows = await cursor.fetchall()
    names = {r[1] for r in rows}
    if not names:
        return
    for col, sql in (
        ("drive_folder_id", "ALTER TABLE sync_info ADD COLUMN drive_folder_id TEXT"),
        (
            "drive_database_file_id",
            "ALTER TABLE sync_info ADD COLUMN drive_database_file_id TEXT",
        ),
        (
            "drive_snapshot_file_id",
            "ALTER TABLE sync_info ADD COLUMN drive_snapshot_file_id TEXT",
        ),
    ):
        if col not in names:
            await db.execute(sql)


async def _migrate_statement_policy_lines_columns(db: aiosqlite.Connection) -> None:
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='statement_policy_lines'"
    ) as cur:
        if not await cur.fetchone():
            return
    async with db.execute("PRAGMA table_info(statement_policy_lines)") as cursor:
        col_names = {r[1] for r in await cursor.fetchall()}
    if "customer_name" not in col_names:
        await db.execute("ALTER TABLE statement_policy_lines ADD COLUMN customer_name TEXT")
        await db.execute("ALTER TABLE statement_policy_lines ADD COLUMN address TEXT")
        col_names |= {"customer_name", "address"}

    # Imported lazily because ``statement_parse`` itself imports nothing
    # from the database layer; the import-time cost only matters when an
    # older DB still has the legacy ``name_and_address`` column.
    from statement_parse import split_name_address

    if "name_and_address" in col_names:
        async with db.execute(
            """SELECT id, name_and_address, customer_name FROM statement_policy_lines
               WHERE customer_name IS NULL OR TRIM(customer_name) = ''"""
        ) as cursor:
            rows = await cursor.fetchall()
        for row in rows:
            rid = row["id"]
            na = row["name_and_address"]
            name, addr = split_name_address(na)
            await db.execute(
                "UPDATE statement_policy_lines SET customer_name = ?, address = ? WHERE id = ?",
                (name, addr, rid),
            )
    else:
        async with db.execute(
            """SELECT id FROM statement_policy_lines
               WHERE customer_name IS NULL OR TRIM(customer_name) = ''"""
        ) as cursor:
            rows = await cursor.fetchall()
        for row in rows:
            await db.execute(
                "UPDATE statement_policy_lines SET customer_name = ?, address = ? WHERE id = ?",
                ("Unknown", None, row["id"]),
            )


__all__ = ["apply_migrations"]
