"""
Tests for the master-data ("Insurance Type" / "Policy Type") taxonomy.

Verifies:
- ``GET /api/insurance-types`` lists the seeded categories.
- ``GET /api/policy-types`` lists the seeded child types.
- The ``insurance_type_id`` filter on ``/api/policy-types`` actually narrows
  the results to that parent.
- ``include_inactive=false`` (the default) hides archived rows; flipping the
  flag returns them again.
- Sending a parent id that doesn't exist returns an empty list rather than 500.

The tests rely only on the seeded defaults from
``database/seed.py::seed_reference_data`` (Motor, Health, Life, Travel,
Property), so they don't depend on test data created by other test modules.
"""

from __future__ import annotations

import sqlite3


SEEDED_CATEGORY_NAMES = {"Motor", "Health", "Life", "Travel", "Property"}


# --------------------------------------------------------------------------- #
# Insurance categories (parent)                                                #
# --------------------------------------------------------------------------- #


def test_list_insurance_types_returns_seeded_defaults(client) -> None:
    r = client.get("/api/insurance-types")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    names = {row["name"] for row in body}
    assert SEEDED_CATEGORY_NAMES <= names, (
        f"missing seeded categories: {SEEDED_CATEGORY_NAMES - names}"
    )
    for row in body:
        assert {"id", "name", "is_active"} <= row.keys()
        assert isinstance(row["id"], int)
        assert isinstance(row["is_active"], bool)


# --------------------------------------------------------------------------- #
# Policy types (child)                                                         #
# --------------------------------------------------------------------------- #


def test_list_policy_types_returns_full_set_by_default(client) -> None:
    r = client.get("/api/policy-types")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    # Each row carries the parent id so the frontend can build the cascade.
    for row in body:
        assert {"id", "name", "insurance_type_id", "is_active"} <= row.keys()


def test_policy_types_filter_by_insurance_type_id_narrows_results(client) -> None:
    cats = client.get("/api/insurance-types").json()
    motor = next(row for row in cats if row["name"] == "Motor")
    health = next(row for row in cats if row["name"] == "Health")

    motor_types = client.get(
        "/api/policy-types", params={"insurance_type_id": motor["id"]}
    ).json()
    health_types = client.get(
        "/api/policy-types", params={"insurance_type_id": health["id"]}
    ).json()

    # All returned rows must belong to the requested parent.
    assert all(t["insurance_type_id"] == motor["id"] for t in motor_types)
    assert all(t["insurance_type_id"] == health["id"] for t in health_types)

    # And the two sets are mutually exclusive.
    motor_ids = {t["id"] for t in motor_types}
    health_ids = {t["id"] for t in health_types}
    assert motor_ids.isdisjoint(health_ids)
    assert motor_ids, "Motor parent should have at least one seeded child"
    assert health_ids, "Health parent should have at least one seeded child"


def test_policy_types_unknown_parent_returns_empty_list(client) -> None:
    r = client.get("/api/policy-types", params={"insurance_type_id": 999_999})
    assert r.status_code == 200
    assert r.json() == []


def test_policy_types_include_inactive_flag(client, app_env) -> None:
    """
    Archive a single seeded policy_type via direct sqlite write, then verify the
    default view hides it but ``include_inactive=true`` brings it back. Using
    sqlite3 (sync) here so this test stays usable on Python builds where
    aiosqlite + pytest crashes.
    """
    db_path = app_env["db_path"]
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, is_active FROM policy_types ORDER BY id LIMIT 1"
        ).fetchone()
        assert row is not None, "expected seeded policy_types row"
        target_id, original_active = row[0], row[1]
        conn.execute("UPDATE policy_types SET is_active = 0 WHERE id = ?", (target_id,))
        conn.commit()
    finally:
        conn.close()

    try:
        active_only = client.get("/api/policy-types").json()
        assert all(t["id"] != target_id for t in active_only), (
            "archived policy_type leaked into active-only list"
        )

        with_inactive = client.get(
            "/api/policy-types", params={"include_inactive": True}
        ).json()
        ids = {t["id"] for t in with_inactive}
        assert target_id in ids, "include_inactive=true should resurface the archived row"
    finally:
        # Restore so subsequent tests in the module see the seeded data unchanged.
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "UPDATE policy_types SET is_active = ? WHERE id = ?",
                (original_active, target_id),
            )
            conn.commit()
        finally:
            conn.close()
