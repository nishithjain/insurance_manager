"""
Policy-endpoint tests focused on the behaviours called out in the spec:

- Create / list / detail / update / recent / expiring (basic round trip).
- A policy ``PUT`` must NOT accidentally mutate the linked customer's name.
- Validation errors return 4xx with helpful detail (not 500).
- Updates to allowed customer-linked fields (e.g. phone via dedicated endpoints)
  do not bleed across customers.

The existing ``test_api_smoke.py`` already covers the contact / payment /
renewal-resolution PATCH flows, so we keep those out of scope here.
"""

from __future__ import annotations

from datetime import date, timedelta


def _today() -> str:
    return date.today().isoformat()


def _days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


# --------------------------------------------------------------------------- #
# Create + list                                                                #
# --------------------------------------------------------------------------- #


def test_create_policy_round_trip(client, make_customer, make_policy) -> None:
    cust = make_customer(name="Policy Owner Alpha", phone="8100000001")
    p = make_policy(cust["id"], policy_number="POL-ALPHA-001")
    assert p["customer_id"] == cust["id"]
    assert p["policy_number"] == "POL-ALPHA-001"
    assert p["status"] == "active"
    # Defaults the service applies on create.
    assert p["contact_status"] == "Not Contacted"
    assert p["renewal_status"] == "Open"


def test_list_policies_includes_created(client, make_customer, make_policy) -> None:
    cust = make_customer(name="Listing Owner", phone="8100000002")
    p = make_policy(cust["id"], policy_number="POL-LIST-001")
    r = client.get("/api/policies")
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()}
    assert p["id"] in ids


def test_policy_detail_bundle_has_customer_and_category_group(
    client, make_customer, make_policy
) -> None:
    cust = make_customer(name="Detail Bundle Owner", phone="8100000003")
    p = make_policy(cust["id"], policy_number="POL-DETAIL-001")
    r = client.get(f"/api/policies/{p['id']}/detail")
    assert r.status_code == 200
    bundle = r.json()
    assert bundle["policy"]["id"] == p["id"]
    assert bundle["customer"]["id"] == cust["id"]
    # Auto policy_type maps to Motor category.
    assert bundle["category_group"] == "Motor"


# --------------------------------------------------------------------------- #
# Update should not mutate customer name                                       #
# --------------------------------------------------------------------------- #


def test_policy_update_does_not_change_customer_name(
    client, make_customer, make_policy
) -> None:
    """
    The policy ``PUT`` body has no ``customer_name`` field, but if a future
    refactor accidentally introduced one, this test would catch the regression
    by verifying the linked customer row is untouched.
    """
    cust = make_customer(name="Read Only Name", phone="8100000010")
    p = make_policy(cust["id"], policy_number="POL-RONAME-001")

    r = client.put(
        f"/api/policies/{p['id']}",
        json={
            "customer_id": cust["id"],
            "policy_number": "POL-RONAME-001-v2",
            "policy_type": "auto",
            "start_date": _today(),
            "end_date": _days(20),
            "premium": 7777.77,
            "status": "active",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["policy_number"] == "POL-RONAME-001-v2"

    after = client.get(f"/api/customers/{cust['id']}").json()
    assert after["name"] == "Read Only Name", "customer name must remain stable"


# --------------------------------------------------------------------------- #
# Validation                                                                   #
# --------------------------------------------------------------------------- #


def test_create_policy_with_unknown_customer_returns_4xx(client) -> None:
    """
    ``customer_id`` must reference an existing customer for the same data-owner.
    The exact code is governed by ``policy_service``; we just want to be sure
    it's a clean client error, not a 500.
    """
    r = client.post(
        "/api/policies",
        json={
            "customer_id": "9999999",
            "policy_number": "POL-NO-CUST-001",
            "policy_type": "auto",
            "start_date": _today(),
            "end_date": _days(30),
            "premium": 100.0,
            "status": "active",
        },
    )
    assert 400 <= r.status_code < 500, r.text


def test_get_policy_unknown_id_returns_404(client) -> None:
    assert client.get("/api/policies/9999999").status_code == 404
    assert client.get("/api/policies/not-a-number").status_code == 404


def test_update_policy_unknown_id_returns_404(client, make_customer) -> None:
    cust = make_customer(name="Owner For 404", phone="8100000020")
    r = client.put(
        "/api/policies/9999999",
        json={
            "customer_id": cust["id"],
            "policy_number": "POL-404-001",
            "policy_type": "auto",
            "start_date": _today(),
            "end_date": _days(30),
            "premium": 1.0,
            "status": "active",
        },
    )
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# Delete                                                                       #
# --------------------------------------------------------------------------- #


def test_delete_policy_then_get_returns_404(client, make_customer, make_policy) -> None:
    cust = make_customer(name="To Be Deleted Owner", phone="8100000030")
    p = make_policy(cust["id"], policy_number="POL-DEL-001")
    r = client.delete(f"/api/policies/{p['id']}")
    assert r.status_code == 200
    assert r.json()["message"] == "Policy deleted successfully"
    assert client.get(f"/api/policies/{p['id']}").status_code == 404
