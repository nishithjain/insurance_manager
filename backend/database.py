import aiosqlite
import os
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import logging
import re

from db_path import DB_PATH
from services.database_backup import DatabaseBackupService

logger = logging.getLogger(__name__)

_WRITE_SQL_RE = re.compile(
    r"^\s*(?:--[^\n]*\n\s*)*(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|VACUUM)\b",
    re.IGNORECASE,
)


class BackupAioSqliteConnection:
    """Thin proxy that runs one configured DB backup before the first write."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db
        self._backup_service = DatabaseBackupService()
        self._backup_checked = False

    def __getattr__(self, name: str):
        return getattr(self._db, name)

    def _is_write_sql(self, sql: str) -> bool:
        return bool(_WRITE_SQL_RE.match(sql or ""))

    async def _backup_before_write_once(self, sql: str) -> None:
        if self._backup_checked or not self._is_write_sql(sql):
            return
        self._backup_service.backup_before_write()
        self._backup_checked = True

    def execute(self, sql: str, parameters=None):
        if parameters is None:
            operation = self._db.execute(sql)
        else:
            operation = self._db.execute(sql, parameters)
        return BackupAioSqliteOperation(
            self._backup_before_write_once(sql),
            operation,
        )

    def executemany(self, sql: str, parameters):
        return BackupAioSqliteOperation(
            self._backup_before_write_once(sql),
            self._db.executemany(sql, parameters),
        )

    def executescript(self, sql_script: str):
        return BackupAioSqliteOperation(
            self._backup_before_write_once(sql_script),
            self._db.executescript(sql_script),
        )


class BackupAioSqliteOperation:
    """Preserve aiosqlite's awaitable + async context manager behavior."""

    def __init__(self, backup_coro, operation) -> None:
        self._backup_coro = backup_coro
        self._operation = operation
        self._backup_done = False

    async def _run_backup_once(self) -> None:
        if self._backup_done:
            return
        await self._backup_coro
        self._backup_done = True

    async def _await_operation(self):
        await self._run_backup_once()
        return await self._operation

    def __await__(self):
        return self._await_operation().__await__()

    async def __aenter__(self):
        await self._run_backup_once()
        return await self._operation.__aenter__()

    async def __aexit__(self, exc_type, exc, tb):
        return await self._operation.__aexit__(exc_type, exc, tb)


# Full schema (normalized policies + per-type detail tables). Multi-tenant via customers.user_id.
SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    picture TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    phone_number TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customer_addresses (
    address_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    address_line1 TEXT,
    address_line2 TEXT,
    area TEXT,
    city TEXT,
    district TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT DEFAULT 'India',
    raw_address TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS agents (
    agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL UNIQUE,
    phone_number TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS insurance_types (
    insurance_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    insurance_type_name TEXT NOT NULL UNIQUE,
    category_group TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payment_statuses (
    payment_status_id INTEGER PRIMARY KEY AUTOINCREMENT,
    status_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS policies (
    policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_record_id TEXT NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL,
    address_id INTEGER,
    insurance_type_id INTEGER NOT NULL,
    company_id INTEGER,
    agent_id INTEGER,
    ncb_discount TEXT,
    total_premium NUMERIC,
    payment_status_id INTEGER,
    date_of_issue TEXT,
    policy_end_date TEXT,
    policy_no TEXT,
    card_details TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    last_contacted_at TEXT,
    contact_status TEXT NOT NULL DEFAULT 'Not Contacted',
    follow_up_date TEXT,
    renewal_status TEXT NOT NULL DEFAULT 'Open',
    renewal_resolution_note TEXT,
    renewal_resolved_at TEXT,
    renewal_resolved_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (address_id) REFERENCES customer_addresses(address_id),
    FOREIGN KEY (insurance_type_id) REFERENCES insurance_types(insurance_type_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (payment_status_id) REFERENCES payment_statuses(payment_status_id)
);

CREATE TABLE IF NOT EXISTS motor_policy_details (
    policy_id INTEGER PRIMARY KEY,
    vehicle_no TEXT,
    vehicle_details TEXT,
    idv_of_vehicle NUMERIC,
    engine_no TEXT,
    chassis_no TEXT,
    od_premium NUMERIC,
    tp_premium NUMERIC,
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS health_policy_details (
    policy_id INTEGER PRIMARY KEY,
    plan_name TEXT,
    sum_insured NUMERIC,
    cover_type TEXT,
    members_covered TEXT,
    base_premium NUMERIC,
    additional_premium NUMERIC,
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS property_policy_details (
    policy_id INTEGER PRIMARY KEY,
    product_name TEXT,
    sum_insured NUMERIC,
    sub_product TEXT,
    risk_location TEXT,
    base_premium NUMERIC,
    additional_premium NUMERIC,
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS renewal_history (
    id TEXT PRIMARY KEY,
    policy_id INTEGER NOT NULL,
    renewal_date TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    last_sync_time TEXT,
    sync_status TEXT,
    file_version TEXT,
    drive_file_id TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS drive_credentials (
    user_id TEXT PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_uri TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_secret TEXT NOT NULL,
    scopes TEXT NOT NULL,
    expiry TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS statement_policy_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    address TEXT,
    phone_number TEXT,
    vehicle_registration TEXT,
    vehicle_details TEXT,
    insurer_company TEXT,
    ncb_or_discount TEXT,
    agent TEXT,
    idv TEXT,
    engine_no TEXT,
    chassis_no TEXT,
    od_premium TEXT,
    tp_premium TEXT,
    premium_total TEXT,
    payment_status TEXT,
    date_of_issue TEXT,
    policy_end_date TEXT,
    policy_number TEXT,
    card_details TEXT,
    source_file TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_policies_customer_id ON policies(customer_id);
CREATE INDEX IF NOT EXISTS idx_policies_policy_no ON policies(policy_no);
CREATE INDEX IF NOT EXISTS idx_policies_issue_date ON policies(date_of_issue);
CREATE INDEX IF NOT EXISTS idx_policies_end_date ON policies(policy_end_date);
CREATE INDEX IF NOT EXISTS idx_policies_insurance_type_id ON policies(insurance_type_id);
CREATE INDEX IF NOT EXISTS idx_motor_vehicle_no ON motor_policy_details(vehicle_no);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);
CREATE INDEX IF NOT EXISTS idx_customers_user ON customers(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_statement_policy_lines_source ON statement_policy_lines(source_file);
CREATE INDEX IF NOT EXISTS idx_statement_policy_lines_policy_no ON statement_policy_lines(policy_number);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Authentication identity (separate from data-owner `users` table).
-- An `app_users` row represents a human who can log in; role decides what they can do.
-- Admins manage this table; regular users never hit it directly.
CREATE TABLE IF NOT EXISTS app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by INTEGER,
    last_login_at TEXT,
    FOREIGN KEY (created_by) REFERENCES app_users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_app_users_email ON app_users(email);
CREATE INDEX IF NOT EXISTS idx_app_users_role ON app_users(role);
"""


async def _migrate_legacy_columns(db: aiosqlite.Connection) -> None:
    """Best-effort upgrades when an older DB file is still present."""
    await _migrate_sync_info_columns(db)
    await _migrate_statement_policy_lines_columns(db)
    await _migrate_policy_contact_columns(db)
    await _migrate_policy_renewal_resolution_columns(db)
    await _migrate_app_settings_table(db)
    await _migrate_policy_payment_columns(db)
    await _migrate_payment_status_vocabulary(db)
    await _bootstrap_initial_admin(db)


async def _bootstrap_initial_admin(db: aiosqlite.Connection) -> None:
    """
    Seed the very first admin from ``INITIAL_ADMIN_EMAIL`` (+ optional
    ``INITIAL_ADMIN_NAME``) when the auth table has no admins yet.

    This is the only way a brand-new deployment gets its first admin — subsequent
    admins are created through the admin UI by an already-logged-in admin. If the
    env var is unset, the function is a no-op and the UI will simply refuse all
    logins (correctly) until an operator seeds one manually.
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

    full_name = (os.environ.get("INITIAL_ADMIN_NAME") or "Administrator").strip() or "Administrator"
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


# Canonical labels (uppercase) — keep in sync with frontend paymentStatus.js
_PAYMENT_STATUS_CANONICAL = (
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


async def _migrate_payment_status_vocabulary(db: aiosqlite.Connection) -> None:
    """Ensure lookup rows exist; normalize legacy 'Pending' → 'PENDING'."""
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='payment_statuses'"
    ) as cur:
        if not await cur.fetchone():
            return
    for label in _PAYMENT_STATUS_CANONICAL:
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
        await db.execute("DELETE FROM payment_statuses WHERE payment_status_id = ?", (old_id,))
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
        ("drive_database_file_id", "ALTER TABLE sync_info ADD COLUMN drive_database_file_id TEXT"),
        ("drive_snapshot_file_id", "ALTER TABLE sync_info ADD COLUMN drive_snapshot_file_id TEXT"),
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


async def _seed_reference_data(db: aiosqlite.Connection) -> None:
    """Lookup rows for insurance types and payment statuses (idempotent)."""
    async with db.execute("SELECT COUNT(*) FROM insurance_types") as cur:
        n = (await cur.fetchone())[0]
    if n == 0:
        rows = [
            ("Private Car", "Motor"),
            ("Two Wheeler", "Motor"),
            ("Health", "Health"),
            ("Property", "Property"),
        ]
        await db.executemany(
            "INSERT INTO insurance_types (insurance_type_name, category_group) VALUES (?, ?)",
            rows,
        )
    async with db.execute("SELECT COUNT(*) FROM payment_statuses") as cur:
        n2 = (await cur.fetchone())[0]
    if n2 == 0:
        for s in _PAYMENT_STATUS_CANONICAL:
            await db.execute(
                """
                INSERT INTO payment_statuses (status_name)
                SELECT ? WHERE NOT EXISTS (SELECT 1 FROM payment_statuses WHERE status_name = ?)
                """,
                (s, s),
            )


async def init_db():
    """Create schema and seed reference data."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        DatabaseBackupService().backup_before_write()
        await db.executescript(SCHEMA_SQL)
        await _migrate_legacy_columns(db)
        await _seed_reference_data(db)
        await db.commit()
        logger.info("Database initialized successfully")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return BackupAioSqliteConnection(db)


def export_user_insurance_sqlite_bytes(user_id: str) -> bytes:
    """
    Build a single-user SQLite export (customers, addresses, policies, detail rows).
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    path = tmp.name
    main = str(DB_PATH)
    try:
        exp = sqlite3.connect(path)
        try:
            exp.execute("PRAGMA foreign_keys = OFF")
            exp.executescript(
                """
                CREATE TABLE customers (
                    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT,
                    phone_number TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE customer_addresses (
                    address_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    address_line1 TEXT,
                    address_line2 TEXT,
                    area TEXT,
                    city TEXT,
                    district TEXT,
                    state TEXT,
                    postal_code TEXT,
                    country TEXT,
                    raw_address TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE insurance_types (
                    insurance_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    insurance_type_name TEXT NOT NULL,
                    category_group TEXT NOT NULL
                );
                CREATE TABLE companies (
                    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL
                );
                CREATE TABLE agents (
                    agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    phone_number TEXT,
                    email TEXT
                );
                CREATE TABLE payment_statuses (
                    payment_status_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status_name TEXT NOT NULL
                );
                CREATE TABLE policies (
                    policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_record_id TEXT NOT NULL,
                    customer_id INTEGER NOT NULL,
                    address_id INTEGER,
                    insurance_type_id INTEGER NOT NULL,
                    company_id INTEGER,
                    agent_id INTEGER,
                    ncb_discount TEXT,
                    total_premium NUMERIC,
                    payment_status_id INTEGER,
                    date_of_issue TEXT,
                    policy_end_date TEXT,
                    policy_no TEXT,
                    card_details TEXT,
                    status TEXT NOT NULL,
                    last_contacted_at TEXT,
                    contact_status TEXT NOT NULL DEFAULT 'Not Contacted',
                    follow_up_date TEXT,
                    renewal_status TEXT NOT NULL DEFAULT 'Open',
                    renewal_resolution_note TEXT,
                    renewal_resolved_at TEXT,
                    renewal_resolved_by TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE motor_policy_details (
                    policy_id INTEGER PRIMARY KEY,
                    vehicle_no TEXT,
                    vehicle_details TEXT,
                    idv_of_vehicle NUMERIC,
                    engine_no TEXT,
                    chassis_no TEXT,
                    od_premium NUMERIC,
                    tp_premium NUMERIC
                );
                CREATE TABLE health_policy_details (
                    policy_id INTEGER PRIMARY KEY,
                    plan_name TEXT,
                    sum_insured NUMERIC,
                    cover_type TEXT,
                    members_covered TEXT,
                    base_premium NUMERIC,
                    additional_premium NUMERIC
                );
                CREATE TABLE property_policy_details (
                    policy_id INTEGER PRIMARY KEY,
                    product_name TEXT,
                    sum_insured NUMERIC,
                    sub_product TEXT,
                    risk_location TEXT,
                    base_premium NUMERIC,
                    additional_premium NUMERIC
                );
                CREATE TABLE renewal_history (
                    id TEXT PRIMARY KEY,
                    policy_id INTEGER NOT NULL,
                    renewal_date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            exp.execute("ATTACH DATABASE ? AS m", (main,))

            exp.execute(
                "INSERT INTO customers SELECT * FROM m.customers WHERE user_id = ?",
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO customer_addresses SELECT ca.*
                FROM m.customer_addresses ca
                INNER JOIN m.customers c ON ca.customer_id = c.customer_id
                WHERE c.user_id = ?
                """,
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO insurance_types SELECT it.*
                FROM m.insurance_types it
                WHERE it.insurance_type_id IN (
                    SELECT DISTINCT p.insurance_type_id FROM m.policies p
                    INNER JOIN m.customers c ON p.customer_id = c.customer_id
                    WHERE c.user_id = ?
                )
                """,
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO companies SELECT co.*
                FROM m.companies co
                WHERE co.company_id IN (
                    SELECT DISTINCT p.company_id FROM m.policies p
                    INNER JOIN m.customers c ON p.customer_id = c.customer_id
                    WHERE c.user_id = ? AND p.company_id IS NOT NULL
                )
                """,
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO agents SELECT a.*
                FROM m.agents a
                WHERE a.agent_id IN (
                    SELECT DISTINCT p.agent_id FROM m.policies p
                    INNER JOIN m.customers c ON p.customer_id = c.customer_id
                    WHERE c.user_id = ? AND p.agent_id IS NOT NULL
                )
                """,
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO payment_statuses SELECT ps.*
                FROM m.payment_statuses ps
                WHERE ps.payment_status_id IN (
                    SELECT DISTINCT p.payment_status_id FROM m.policies p
                    INNER JOIN m.customers c ON p.customer_id = c.customer_id
                    WHERE c.user_id = ? AND p.payment_status_id IS NOT NULL
                )
                """,
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO policies SELECT p.*
                FROM m.policies p
                INNER JOIN m.customers c ON p.customer_id = c.customer_id
                WHERE c.user_id = ?
                """,
                (user_id,),
            )
            for detail in (
                "motor_policy_details",
                "health_policy_details",
                "property_policy_details",
            ):
                exp.execute(
                    f"""
                    INSERT INTO {detail} SELECT d.*
                    FROM m.{detail} d
                    INNER JOIN m.policies p ON d.policy_id = p.policy_id
                    INNER JOIN m.customers c ON p.customer_id = c.customer_id
                    WHERE c.user_id = ?
                    """,
                    (user_id,),
                )
            exp.execute(
                """
                INSERT INTO renewal_history SELECT rh.*
                FROM m.renewal_history rh
                INNER JOIN m.policies p ON rh.policy_id = p.policy_id
                INNER JOIN m.customers c ON p.customer_id = c.customer_id
                WHERE c.user_id = ?
                """,
                (user_id,),
            )
            exp.commit()
            exp.execute("DETACH DATABASE m")
        finally:
            exp.close()
        return Path(path).read_bytes()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
