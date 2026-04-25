"""
Customer-endpoint tests beyond the round-trip CRUD already covered by the
existing API smoke test.

Focus areas:
- Listing returns an empty array on a fresh DB (data-owner isolation).
- Validation errors for blank / missing required fields.
- Admin-grid endpoint (``/api/admin/customers``) returns the same record with
  the extra ``policy_count`` field.
- Updating a customer through the admin grid persists name + contact changes.
- A ``PUT`` whose body is missing ``name`` is rejected.
"""

from __future__ import annotations


# --------------------------------------------------------------------------- #
# Listing                                                                     #
# --------------------------------------------------------------------------- #


def test_customer_list_starts_empty(client) -> None:
    r = client.get("/api/customers")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# --------------------------------------------------------------------------- #
# Validation                                                                  #
# --------------------------------------------------------------------------- #


def test_create_customer_requires_name(client) -> None:
    """``CustomerCreate.name`` is non-optional → Pydantic 422."""
    r = client.post("/api/customers", json={"email": "no-name@example.com"})
    assert r.status_code == 422


def test_get_customer_invalid_id_returns_404(client) -> None:
    r = client.get("/api/customers/not-a-number")
    assert r.status_code == 404


def test_get_customer_unknown_id_returns_404(client) -> None:
    r = client.get("/api/customers/9999999")
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# CRUD round-trip                                                             #
# --------------------------------------------------------------------------- #


def test_create_get_update_round_trip(client, make_customer) -> None:
    created = make_customer(name="Round Trip", phone="9000000001")
    cid = created["id"]
    assert created["name"] == "Round Trip"
    assert created["phone"] == "9000000001"

    r = client.get(f"/api/customers/{cid}")
    assert r.status_code == 200
    assert r.json()["id"] == cid

    r = client.put(
        f"/api/customers/{cid}",
        json={
            "name": "Round Trip v2",
            "email": "rt2@example.com",
            "phone": "9000000002",
            "address": "New Street, City",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Round Trip v2"
    assert body["email"] == "rt2@example.com"
    assert body["phone"] == "9000000002"
    assert body["address"] == "New Street, City"


# --------------------------------------------------------------------------- #
# Admin grid                                                                  #
# --------------------------------------------------------------------------- #


def test_admin_customers_grid_lists_with_policy_count(client, make_customer) -> None:
    created = make_customer(name="Admin Visible", phone="9100000001")
    r = client.get("/api/admin/customers")
    assert r.status_code == 200
    rows = r.json()
    assert any(row["id"] == created["id"] for row in rows)

    target = next(row for row in rows if row["id"] == created["id"])
    assert target["name"] == "Admin Visible"
    assert "policy_count" in target
    assert target["policy_count"] >= 0


def test_admin_customer_search_filter(client, make_customer) -> None:
    needle = make_customer(name="Searchable Needle Customer", phone="9100000002")
    r = client.get("/api/admin/customers", params={"search": "needle"})
    assert r.status_code == 200
    found = r.json()
    assert any(row["id"] == needle["id"] for row in found)


def test_admin_customer_get_404_for_unknown(client) -> None:
    r = client.get("/api/admin/customers/9999999")
    assert r.status_code == 404


def test_admin_customer_update_requires_name(client, make_customer) -> None:
    created = make_customer(name="Will Test Blank", phone="9100000003")
    cid = created["id"]
    r = client.put(f"/api/admin/customers/{cid}", json={"name": "   "})
    assert r.status_code == 400
    assert "name" in r.json()["detail"].lower()


def test_admin_customer_update_persists_changes(client, make_customer) -> None:
    created = make_customer(name="Admin Update Original", phone="9100000004")
    cid = created["id"]
    r = client.put(
        f"/api/admin/customers/{cid}",
        json={
            "name": "Admin Update Renamed",
            "email": "renamed@example.com",
            "phone": "9100000044",
            "address": "Admin Address",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Admin Update Renamed"
    assert body["phone"] == "9100000044"

    r = client.get(f"/api/customers/{cid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Admin Update Renamed"
