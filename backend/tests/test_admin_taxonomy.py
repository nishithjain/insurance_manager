"""
Tests for the admin "Insurance Master" CRUD endpoints.

Covers:
- Insurance Type create / list / get / update / duplicate / delete (hard + soft).
- Policy Type create / list / get / update / duplicate-under-same-parent / move
  to another parent / delete (hard + soft).
- Validation: blank names, whitespace trimming, missing/invalid parent.
- Auth: every admin endpoint rejects non-admin callers.
- Soft-delete-when-in-use: a policy referencing the row flips ``is_active``
  off instead of deleting it.

Tests intentionally use unique generated names so they're order-independent
and do not collide with the seeded canonical defaults.
"""

from __future__ import annotations

import uuid

import pytest


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _unique_name(prefix: str) -> str:
    return f"{prefix} {uuid.uuid4().hex[:8]}"


def _create_insurance_type(client, name: str | None = None, **fields):
    payload = {"name": name or _unique_name("Test IT"), **fields}
    r = client.post("/api/admin/insurance-types", json=payload)
    return r


def _create_policy_type(client, parent_id: int, name: str | None = None, **fields):
    payload = {
        "insurance_type_id": parent_id,
        "name": name or _unique_name("Test PT"),
        **fields,
    }
    r = client.post("/api/admin/policy-types", json=payload)
    return r


# --------------------------------------------------------------------------- #
# Insurance Type CRUD                                                          #
# --------------------------------------------------------------------------- #


def test_admin_list_insurance_types_includes_seeded_defaults(client) -> None:
    """The seven canonical categories must surface, including new ones."""
    r = client.get("/api/admin/insurance-types")
    assert r.status_code == 200, r.text
    body = r.json()
    names = {row["name"] for row in body}
    expected = {"Motor", "Health", "Life", "Travel", "Property", "Commercial", "Other"}
    assert expected <= names, f"missing seeded categories: {expected - names}"
    for row in body:
        assert {"id", "name", "is_active", "in_use", "policy_type_count"} <= row.keys()
        assert isinstance(row["id"], int)
        assert isinstance(row["is_active"], bool)
        assert isinstance(row["policy_type_count"], int)


def test_admin_create_insurance_type_trims_and_persists_description(client) -> None:
    name = _unique_name("Crop")
    r = _create_insurance_type(
        client, name=f"  {name}  ", description="  Crop & livestock cover  "
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == name
    assert body["description"] == "Crop & livestock cover"
    assert body["is_active"] is True
    assert body["in_use"] is False


def test_admin_create_insurance_type_rejects_blank_name(client) -> None:
    r = _create_insurance_type(client, name="   ")
    assert r.status_code == 422


def test_admin_create_insurance_type_rejects_duplicate(client) -> None:
    name = _unique_name("Aviation")
    assert _create_insurance_type(client, name=name).status_code == 201
    again = _create_insurance_type(client, name=name)
    assert again.status_code == 409
    different_case = _create_insurance_type(client, name=name.upper())
    assert different_case.status_code == 409


def test_admin_get_insurance_type_returns_full_payload(client) -> None:
    name = _unique_name("Pet")
    created = _create_insurance_type(client, name=name, description="Pet care").json()
    r = client.get(f"/api/admin/insurance-types/{created['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == name
    assert body["description"] == "Pet care"
    assert body["created_at"]
    assert body["updated_at"]


def test_admin_get_insurance_type_404_for_unknown_id(client) -> None:
    r = client.get("/api/admin/insurance-types/999999")
    assert r.status_code == 404


def test_admin_update_insurance_type_changes_fields(client) -> None:
    created = _create_insurance_type(client, name=_unique_name("Cyber")).json()
    r = client.put(
        f"/api/admin/insurance-types/{created['id']}",
        json={"description": "Cyber risk", "is_active": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["description"] == "Cyber risk"
    assert body["is_active"] is False
    assert body["name"] == created["name"]


def test_admin_update_insurance_type_rejects_duplicate_rename(client) -> None:
    a = _create_insurance_type(client, name=_unique_name("Drone")).json()
    b = _create_insurance_type(client, name=_unique_name("Drone")).json()
    r = client.put(
        f"/api/admin/insurance-types/{b['id']}", json={"name": a["name"]}
    )
    assert r.status_code == 409


def test_admin_delete_insurance_type_hard_deletes_when_unused(client) -> None:
    created = _create_insurance_type(client, name=_unique_name("Marine-Test")).json()
    r = client.delete(f"/api/admin/insurance-types/{created['id']}")
    assert r.status_code == 200
    assert r.json()["outcome"] == "deleted"
    assert client.get(f"/api/admin/insurance-types/{created['id']}").status_code == 404


# --------------------------------------------------------------------------- #
# Policy Type CRUD                                                            #
# --------------------------------------------------------------------------- #


@pytest.fixture()
def fresh_parent(client) -> dict:
    """Brand-new Insurance Type guaranteed not to collide with seeded data."""
    r = _create_insurance_type(client, name=_unique_name("Parent"))
    assert r.status_code == 201, r.text
    return r.json()


def test_admin_list_policy_types_filters_by_parent(client, fresh_parent) -> None:
    name = _unique_name("Variant")
    created = _create_policy_type(client, fresh_parent["id"], name=name).json()
    r = client.get(
        "/api/admin/policy-types",
        params={"insurance_type_id": fresh_parent["id"]},
    )
    assert r.status_code == 200
    rows = r.json()
    assert any(row["id"] == created["id"] for row in rows)
    assert all(row["insurance_type_id"] == fresh_parent["id"] for row in rows)


def test_admin_create_policy_type_under_parent(client, fresh_parent) -> None:
    name = _unique_name("Cover")
    r = _create_policy_type(
        client, fresh_parent["id"], name=name, description="Special cover"
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["insurance_type_id"] == fresh_parent["id"]
    assert body["insurance_type_name"] == fresh_parent["name"]
    assert body["name"] == name
    assert body["description"] == "Special cover"
    assert body["in_use"] is False


def test_admin_create_policy_type_rejects_unknown_parent(client) -> None:
    r = _create_policy_type(client, parent_id=999999, name=_unique_name("Orphan"))
    assert r.status_code == 400


def test_admin_create_policy_type_rejects_blank_name(client, fresh_parent) -> None:
    r = _create_policy_type(client, fresh_parent["id"], name="   ")
    assert r.status_code == 422


def test_admin_create_policy_type_rejects_duplicate_in_same_parent(
    client, fresh_parent
) -> None:
    name = _unique_name("Dup")
    assert (
        _create_policy_type(client, fresh_parent["id"], name=name).status_code == 201
    )
    again = _create_policy_type(client, fresh_parent["id"], name=name)
    assert again.status_code == 409


def test_admin_create_policy_type_allows_duplicate_in_different_parent(client) -> None:
    parent_a = _create_insurance_type(client, name=_unique_name("ParA")).json()
    parent_b = _create_insurance_type(client, name=_unique_name("ParB")).json()
    name = _unique_name("Shared")
    r1 = _create_policy_type(client, parent_a["id"], name=name)
    r2 = _create_policy_type(client, parent_b["id"], name=name)
    assert r1.status_code == 201
    assert r2.status_code == 201


def test_admin_update_policy_type_can_move_between_parents(client) -> None:
    parent_a = _create_insurance_type(client, name=_unique_name("Move-A")).json()
    parent_b = _create_insurance_type(client, name=_unique_name("Move-B")).json()
    pt = _create_policy_type(client, parent_a["id"], name=_unique_name("Mover")).json()

    r = client.put(
        f"/api/admin/policy-types/{pt['id']}",
        json={"insurance_type_id": parent_b["id"]},
    )
    assert r.status_code == 200, r.text
    moved = r.json()
    assert moved["insurance_type_id"] == parent_b["id"]
    assert moved["insurance_type_name"] == parent_b["name"]


def test_admin_update_policy_type_collision_after_move(client) -> None:
    parent_a = _create_insurance_type(client, name=_unique_name("Col-A")).json()
    parent_b = _create_insurance_type(client, name=_unique_name("Col-B")).json()
    name = _unique_name("Conflict")
    _create_policy_type(client, parent_b["id"], name=name)
    src = _create_policy_type(client, parent_a["id"], name=name).json()

    r = client.put(
        f"/api/admin/policy-types/{src['id']}",
        json={"insurance_type_id": parent_b["id"]},
    )
    assert r.status_code == 409


def test_admin_delete_policy_type_hard_deletes_when_unused(client, fresh_parent) -> None:
    pt = _create_policy_type(
        client, fresh_parent["id"], name=_unique_name("Disposable")
    ).json()
    r = client.delete(f"/api/admin/policy-types/{pt['id']}")
    assert r.status_code == 200
    assert r.json()["outcome"] == "deleted"
    assert client.get(f"/api/admin/policy-types/{pt['id']}").status_code == 404


# --------------------------------------------------------------------------- #
# Soft-delete on in-use rows                                                  #
# --------------------------------------------------------------------------- #


def test_delete_policy_type_in_use_deactivates(
    client, make_customer, make_policy
) -> None:
    """Creating a policy that references a Policy Type must protect it from hard delete."""
    parent = _create_insurance_type(client, name=_unique_name("Used-Parent")).json()
    pt = _create_policy_type(
        client, parent["id"], name=_unique_name("Used-Variant")
    ).json()

    cust = make_customer(name="Used Owner", phone="8200000001")
    # The policy creation API accepts ``policy_type_id`` (new taxonomy field).
    from datetime import date, timedelta

    body = {
        "customer_id": cust["id"],
        "policy_number": _unique_name("POL-USE"),
        "policy_type": "auto",
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=180)).isoformat(),
        "premium": 999.0,
        "status": "active",
        "policy_type_id": pt["id"],
    }
    r = client.post("/api/policies", json=body)
    assert r.status_code == 200, r.text

    deletion = client.delete(f"/api/admin/policy-types/{pt['id']}")
    assert deletion.status_code == 200
    payload = deletion.json()
    assert payload["outcome"] == "deactivated"
    assert payload["item"]["is_active"] is False

    fetched = client.get(f"/api/admin/policy-types/{pt['id']}").json()
    assert fetched["in_use"] is True
    assert fetched["is_active"] is False


def test_delete_insurance_type_in_use_deactivates(
    client, make_customer
) -> None:
    parent = _create_insurance_type(client, name=_unique_name("Used-IT")).json()
    pt = _create_policy_type(
        client, parent["id"], name=_unique_name("Anchor")
    ).json()

    cust = make_customer(name="Anchor Owner", phone="8200000002")
    from datetime import date, timedelta

    body = {
        "customer_id": cust["id"],
        "policy_number": _unique_name("POL-IT"),
        "policy_type": "auto",
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=180)).isoformat(),
        "premium": 100.0,
        "status": "active",
        "policy_type_id": pt["id"],
    }
    assert client.post("/api/policies", json=body).status_code == 200

    deletion = client.delete(f"/api/admin/insurance-types/{parent['id']}")
    assert deletion.status_code == 200
    payload = deletion.json()
    assert payload["outcome"] == "deactivated"

    fetched = client.get(f"/api/admin/insurance-types/{parent['id']}").json()
    assert fetched["in_use"] is True
    assert fetched["is_active"] is False


# --------------------------------------------------------------------------- #
# Auth                                                                        #
# --------------------------------------------------------------------------- #


def test_admin_taxonomy_endpoints_reject_non_admin(client, app_env) -> None:
    """A logged-in non-admin should see 403 for every admin master endpoint."""
    import sqlite3

    from datetime import datetime, timezone

    db_path = app_env["db_path"]
    conn = sqlite3.connect(db_path)
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO app_users
                 (email, full_name, role, is_active, created_at, updated_at)
               VALUES (?, ?, 'user', 1, ?, ?)""",
            ("non.admin.master@example.com", "Non Admin Master", now, now),
        )
        row = conn.execute(
            "SELECT id FROM app_users WHERE email = ?",
            ("non.admin.master@example.com",),
        ).fetchone()
        conn.commit()
    finally:
        conn.close()

    user_token = app_env["sign"](row[0], "non.admin.master@example.com", "user")
    saved = client.headers.get("Authorization")
    client.headers["Authorization"] = f"Bearer {user_token}"
    try:
        for url, method, payload in [
            ("/api/admin/insurance-types", "GET", None),
            ("/api/admin/insurance-types/1", "GET", None),
            ("/api/admin/insurance-types", "POST", {"name": "Nope"}),
            ("/api/admin/insurance-types/1", "PUT", {"name": "Nope"}),
            ("/api/admin/insurance-types/1", "DELETE", None),
            ("/api/admin/policy-types", "GET", None),
            ("/api/admin/policy-types/1", "GET", None),
            (
                "/api/admin/policy-types",
                "POST",
                {"insurance_type_id": 1, "name": "Nope"},
            ),
            ("/api/admin/policy-types/1", "PUT", {"name": "Nope"}),
            ("/api/admin/policy-types/1", "DELETE", None),
        ]:
            r = client.request(method, url, json=payload)
            assert r.status_code == 403, (
                f"{method} {url} expected 403, got {r.status_code}: {r.text}"
            )
    finally:
        if saved is not None:
            client.headers["Authorization"] = saved
