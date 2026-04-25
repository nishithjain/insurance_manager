"""
Tests for the post-split repository modules.

We exercise:

* the row→schema mappers (pure functions — no DB needed),
* the legacy ``repositories.sql`` re-export shim (every previously public
  name still resolves to the same object as the new home),
* the taxonomy / payment-status DB helpers against an in-memory SQLite
  fixture so we don't touch the real ``insurance.db``.
"""

from __future__ import annotations

import asyncio

import aiosqlite
import pytest

from repositories import sql as sql_shim
from repositories._helpers import maybe_int, sql_float
from repositories.customer_repo import (
    CUSTOMER_ADMIN_SELECT,
    CUSTOMER_SELECT,
    customer_admin_row_to_model,
    customer_row_to_model,
)
from repositories.insurance_type_repo import (
    get_insurance_category_id_by_name,
    get_policy_type_with_category,
    resolve_legacy_insurance_type_for_category,
)
from repositories.payment_status_repo import (
    default_payment_status_id,
    payment_status_id_by_name,
)
from repositories.policy_repo import (
    EXPORT_POLICY_SELECT,
    POLICY_SELECT,
    policy_row_to_model,
)


# --------------------------------------------------------------------------- #
# Pure helpers                                                                #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "value, expected",
    [(None, None), ("", None), ("12.5", 12.5), (3, 3.0), ("nope", None)],
)
def test_sql_float_handles_messy_inputs(value, expected) -> None:
    assert sql_float(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [(None, None), ("3", 3), (5, 5), ("nope", None), ("", None)],
)
def test_maybe_int_handles_messy_inputs(value, expected) -> None:
    assert maybe_int(value) == expected


def test_customer_row_mapper_normalises_blanks() -> None:
    row = {
        "id": 1,
        "user_id": "u",
        "name": None,
        "email": None,
        "phone": None,
        "address": None,
        "created_at": None,
    }
    c = customer_row_to_model(row)
    assert c.id == "1"
    assert c.name == ""
    assert c.created_at == ""


def test_customer_admin_row_mapper_normalises_policy_count() -> None:
    row = {
        "id": 7,
        "user_id": "u",
        "name": "Alice",
        "email": None,
        "phone": None,
        "address": None,
        "created_at": "t",
        "updated_at": None,
        "policy_count": "not-a-number",
    }
    out = customer_admin_row_to_model(row)
    assert out.policy_count == 0


def test_policy_row_mapper_defaults() -> None:
    row = {
        "id": 1,
        "user_id": "u",
        "customer_id": 2,
        "policy_number": "P/1",
        "policy_type": "Private Car",
        "insurer_company": None,
        "payment_status": None,
        "payment_note": None,
        "payment_updated_at": None,
        "start_date": "2025-01-01",
        "end_date": "2026-01-01",
        "premium": "broken-text",
        "status": None,
        "created_at": None,
        "last_contacted_at": None,
        "contact_status": None,
        "follow_up_date": None,
        "renewal_status": None,
        "renewal_resolution_note": None,
        "renewal_resolved_at": None,
        "renewal_resolved_by": None,
        "policy_type_id": None,
        "policy_type_name": None,
        "insurance_type_id": None,
        "insurance_type_name": "Motor",
    }
    p = policy_row_to_model(row)
    assert p.premium == 0.0  # unparseable → 0
    assert p.status == "active"
    assert p.contact_status == "Not Contacted"
    assert p.renewal_status == "Open"
    assert p.insurance_type_name == "Motor"


# --------------------------------------------------------------------------- #
# Re-export shim                                                              #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "name",
    [
        "CUSTOMER_SELECT",
        "CUSTOMER_ADMIN_SELECT",
        "POLICY_SELECT",
        "EXPORT_POLICY_SELECT",
        "parse_customer_id",
        "parse_policy_id",
        "sql_float",
        "customer_row_to_model",
        "customer_admin_row_to_model",
        "policy_row_to_model",
        "resolve_insurance_type_id",
        "default_payment_status_id",
        "insert_empty_policy_detail",
        "get_insurance_category_id_by_name",
        "get_policy_type_with_category",
        "resolve_legacy_insurance_type_for_category",
        "payment_status_id_by_name",
    ],
)
def test_sql_shim_reexports_every_legacy_name(name) -> None:
    assert hasattr(sql_shim, name), f"repositories.sql.{name} is missing"


def test_sql_shim_reexport_identity() -> None:
    """The re-export must be the *same* object as the focused module's symbol."""
    # Re-import both ends *inside* the test. Other test modules may have
    # cleared backend modules out of ``sys.modules`` to point the app at a
    # temp DB; that leaves the file-level ``sql_shim`` alias bound to a
    # stale module while the freshly imported ``policy_repo`` is the new
    # one. Re-importing both here makes the identity assertion stable
    # regardless of test execution order.
    import importlib

    fresh_sql_shim = importlib.import_module("repositories.sql")
    fresh_policy_repo = importlib.import_module("repositories.policy_repo")

    assert fresh_sql_shim.POLICY_SELECT is fresh_policy_repo.POLICY_SELECT


def test_select_fragments_have_required_columns() -> None:
    """Pin a few column aliases so accidental SELECT edits are caught early."""
    assert "AS policy_type_id" in POLICY_SELECT
    assert "AS insurance_type_name" in POLICY_SELECT
    assert "AS coverage_category" in EXPORT_POLICY_SELECT
    assert "AS customer_address" in EXPORT_POLICY_SELECT
    assert "AS policy_count" in CUSTOMER_ADMIN_SELECT
    assert "AS phone" in CUSTOMER_SELECT


# --------------------------------------------------------------------------- #
# DB helpers — in-memory SQLite fixture                                       #
# --------------------------------------------------------------------------- #


SCHEMA_DDL = """
    CREATE TABLE insurance_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        is_active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE insurance_types (
        insurance_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
        insurance_type_name TEXT NOT NULL UNIQUE,
        category_group TEXT
    );
    CREATE TABLE policy_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insurance_category_id INTEGER NOT NULL REFERENCES insurance_categories(id),
        name TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE payment_statuses (
        payment_status_id INTEGER PRIMARY KEY AUTOINCREMENT,
        status_name TEXT NOT NULL UNIQUE
    );
    INSERT INTO insurance_categories (name) VALUES ('Motor'), ('Health'), ('Life');
    INSERT INTO insurance_types (insurance_type_name, category_group)
        VALUES ('Private Car', 'Motor'), ('Family Floater', 'Health');
    INSERT INTO policy_types (insurance_category_id, name)
        VALUES (1, 'Comprehensive'), (2, 'Family Floater');
    INSERT INTO payment_statuses (status_name)
        VALUES ('Unknown'), ('PAID');
"""


async def _open_seeded_db() -> aiosqlite.Connection:
    """Spin up a per-test in-memory SQLite preloaded with the helper schema."""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.executescript(SCHEMA_DDL)
    await db.commit()
    return db


def _run_with_db(work):
    """
    Execute an ``async (db) -> result`` callable against a fresh seeded DB.

    Each test gets its own ``asyncio.run`` invocation (matching the pattern
    already used in ``test_api_smoke.py`` / ``test_auth_and_admin.py``) which
    avoids mixing event loops across tests and keeps the helper isolated
    from any pytest-level loop policy.
    """

    async def _runner():
        db = await _open_seeded_db()
        try:
            return await work(db)
        finally:
            await db.close()

    return asyncio.run(_runner())


def test_get_insurance_category_id_is_case_insensitive() -> None:
    out = _run_with_db(lambda db: get_insurance_category_id_by_name(db, "motor"))
    assert out == 1


def test_get_insurance_category_id_unknown_returns_none() -> None:
    out = _run_with_db(lambda db: get_insurance_category_id_by_name(db, "Cyber"))
    assert out is None


def test_get_policy_type_with_category_joins_parent() -> None:
    out = _run_with_db(lambda db: get_policy_type_with_category(db, 1))
    assert out is not None
    assert out["name"] == "Comprehensive"
    assert out["insurance_category_id"] == 1
    assert out["insurance_category_name"] == "Motor"


def test_get_policy_type_with_category_missing_returns_none() -> None:
    out = _run_with_db(lambda db: get_policy_type_with_category(db, 999))
    assert out is None


def test_resolve_legacy_existing_category_picks_first() -> None:
    """Motor already has a row → no auto-create, returns its FK id."""
    out = _run_with_db(
        lambda db: resolve_legacy_insurance_type_for_category(db, "Motor")
    )
    assert out == 1


def test_resolve_legacy_unknown_category_auto_creates() -> None:
    """Life has no legacy row → helper inserts one and returns its FK id."""

    async def _both(db):
        first = await resolve_legacy_insurance_type_for_category(db, "Life")
        second = await resolve_legacy_insurance_type_for_category(db, "Life")
        return first, second

    first, second = _run_with_db(_both)
    assert first >= 1 and first == second  # idempotent


def test_default_payment_status_id_finds_unknown() -> None:
    out = _run_with_db(lambda db: default_payment_status_id(db))
    assert out == 1


def test_payment_status_id_by_name_case_sensitive() -> None:
    """The status_name lookup is exact — that matches existing call sites."""

    async def _both(db):
        return (
            await payment_status_id_by_name(db, "PAID"),
            await payment_status_id_by_name(db, "missing"),
        )

    paid, missing = _run_with_db(_both)
    assert paid == 2 and missing is None
