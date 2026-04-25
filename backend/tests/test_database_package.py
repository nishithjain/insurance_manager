"""
Tests for the ``database/`` package split.

Two concerns are exercised:

1. Backward-compatibility shim — every legacy symbol that used to live on
   the flat ``database`` module is still importable from
   ``database`` after the split.
2. Internal contract of the schema/seed pieces — the constants are
   well-formed (no duplicates, all policy-type categories actually exist
   in the parent list) and the SQL is syntactically valid SQLite.

We deliberately avoid touching ``aiosqlite`` here because the project's
async DB tests can crash this developer's particular Python build (a
``bmcpython`` patched runtime). Plain ``sqlite3`` works fine and gives
us the same level of guarantee for the static SQL we ship.
"""

from __future__ import annotations

import importlib
import sqlite3

import pytest

LEGACY_PUBLIC_SYMBOLS = (
    "init_db",
    "get_db",
    "BackupAioSqliteConnection",
    "BackupAioSqliteOperation",
    "SCHEMA_SQL",
    "export_user_insurance_sqlite_bytes",
)


@pytest.mark.parametrize("symbol", LEGACY_PUBLIC_SYMBOLS)
def test_legacy_symbol_still_importable(symbol: str) -> None:
    db = importlib.import_module("database")
    assert hasattr(db, symbol), f"database.{symbol} disappeared after the split"


def test_init_db_resolves_to_connection_module() -> None:
    db = importlib.import_module("database")
    conn = importlib.import_module("database.connection")
    assert db.init_db is conn.init_db
    assert db.get_db is conn.get_db


def test_schema_sql_is_valid_sqlite() -> None:
    """Run SCHEMA_SQL against an in-memory SQLite to prove it is valid DDL."""
    schema = importlib.import_module("database.schema")
    db = sqlite3.connect(":memory:")
    try:
        db.executescript(schema.SCHEMA_SQL)
        rows = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {r[0] for r in rows}
    finally:
        db.close()
    expected = {
        "users",
        "user_sessions",
        "customers",
        "customer_addresses",
        "companies",
        "agents",
        "insurance_types",
        "insurance_categories",
        "policy_types",
        "payment_statuses",
        "policies",
        "motor_policy_details",
        "health_policy_details",
        "property_policy_details",
        "renewal_history",
        "sync_info",
        "drive_credentials",
        "statement_policy_lines",
        "app_settings",
        "app_users",
    }
    missing = expected - names
    assert not missing, f"SCHEMA_SQL is missing tables: {sorted(missing)}"


def test_policy_type_defaults_reference_known_categories() -> None:
    """Every parent in POLICY_TYPE_DEFAULTS must exist in INSURANCE_CATEGORY_DEFAULTS."""
    seed = importlib.import_module("database.seed")
    parents = {p for p, _ in seed.POLICY_TYPE_DEFAULTS}
    known = set(seed.INSURANCE_CATEGORY_DEFAULTS)
    orphans = parents - known
    assert not orphans, f"policy types reference unknown categories: {orphans}"


def test_payment_status_canonical_unique() -> None:
    seed = importlib.import_module("database.seed")
    labels = list(seed.PAYMENT_STATUS_CANONICAL)
    assert len(labels) == len(set(labels)), "Duplicate payment status label in seed"
    assert "PENDING" in labels, "Canonical 'PENDING' must exist for new-policy default"


def test_write_sql_regex_classifies_correctly() -> None:
    """The backup-on-first-write proxy relies on this regex; lock it down."""
    conn = importlib.import_module("database.connection")
    rgx = conn._WRITE_SQL_RE

    write_examples = [
        "INSERT INTO foo VALUES (1)",
        "  update foo set x=1",
        "DELETE FROM bar",
        "REPLACE INTO foo VALUES (1)",
        "CREATE TABLE x (id INTEGER)",
        "DROP TABLE x",
        "ALTER TABLE x ADD COLUMN y TEXT",
        "VACUUM",
        "-- a comment\nINSERT INTO foo VALUES (1)",
    ]
    read_examples = [
        "SELECT * FROM foo",
        "  pragma table_info(foo)",
        "EXPLAIN SELECT 1",
        "",
    ]
    for sql in write_examples:
        assert rgx.match(sql), f"Expected write match: {sql!r}"
    for sql in read_examples:
        assert not rgx.match(sql), f"Expected non-write: {sql!r}"
