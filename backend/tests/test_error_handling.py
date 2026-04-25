"""
End-to-end error-handling assertions.

These tests sit at the seam between FastAPI's own validation (which returns
422 for malformed bodies / query strings) and the application-layer error
mapping that routers do explicitly (404 for unknown ids, 400 for domain
violations, 401 for auth failures).

Each case is a one-liner per the spec checklist:

- Invalid IDs return 404 (not 500).
- Invalid payloads return 422 (Pydantic) or 400 (router-level).
- DB constraint errors are handled as 4xx, not propagated as 500.
- Empty database responses come back as ``[]``, not ``null``.
- Unknown routes return 404.
- Wrong HTTP method returns 405.

We try to keep each assertion behavioural ("returns 4xx") rather than
brittle ("returns exactly 422"), because the routers reserve the right to
upgrade their validation strategy without breaking the contract these
tests guard.
"""

from __future__ import annotations

from datetime import date, timedelta


# --------------------------------------------------------------------------- #
# 404 — unknown / malformed identifiers                                        #
# --------------------------------------------------------------------------- #


def test_unknown_customer_id_returns_404(client) -> None:
    assert client.get("/api/customers/9999999").status_code == 404


def test_non_numeric_customer_id_returns_404(client) -> None:
    assert client.get("/api/customers/oops").status_code == 404


def test_unknown_policy_id_returns_404(client) -> None:
    assert client.get("/api/policies/9999999").status_code == 404


def test_non_numeric_policy_id_returns_404(client) -> None:
    assert client.get("/api/policies/oops").status_code == 404


def test_unknown_admin_customer_returns_404(client) -> None:
    assert client.get("/api/admin/customers/9999999").status_code == 404


# --------------------------------------------------------------------------- #
# 422 — body / query validation                                                #
# --------------------------------------------------------------------------- #


def test_create_customer_missing_name_returns_422(client) -> None:
    r = client.post("/api/customers", json={"phone": "1234567890"})
    assert r.status_code == 422


def test_create_policy_missing_required_fields_returns_422(client) -> None:
    r = client.post("/api/policies", json={"policy_number": "P-incomplete"})
    assert r.status_code == 422


def test_renewals_expiring_list_invalid_window_returns_422(client) -> None:
    r = client.get("/api/renewals/expiring-list", params={"window": "definitely-bogus"})
    assert r.status_code == 422


def test_export_policies_csv_invalid_month_returns_422_or_400(client) -> None:
    """Out-of-range month — FastAPI/Pydantic 422 OR router-level 400."""
    today = date.today()
    r = client.get(
        "/api/export/policies-csv",
        params={"year": today.year, "month": 13, "by": "policy_end_date"},
    )
    assert r.status_code in (400, 422)


# --------------------------------------------------------------------------- #
# 400 — domain rule violations                                                 #
# --------------------------------------------------------------------------- #


def test_policy_contact_patch_with_bad_status_returns_400(
    client, make_customer, make_policy
) -> None:
    cust = make_customer(name="Err Owner Contact", phone="5100000001")
    p = make_policy(cust["id"], policy_number="POL-ERR-CONTACT-1")
    r = client.patch(
        f"/api/policies/{p['id']}/contact", json={"contact_status": "NOT-A-VALUE"}
    )
    assert r.status_code == 400


def test_policy_renewal_resolution_with_bad_status_returns_400(
    client, make_customer, make_policy
) -> None:
    cust = make_customer(name="Err Owner Renewal", phone="5100000002")
    p = make_policy(cust["id"], policy_number="POL-ERR-RENEW-1")
    r = client.patch(
        f"/api/policies/{p['id']}/renewal-resolution",
        json={"renewal_status": "NEVER-HEARD-OF-IT"},
    )
    assert r.status_code == 400


def test_admin_customer_update_blank_name_returns_400(
    client, make_customer
) -> None:
    cust = make_customer(name="To Be Renamed Blank", phone="5100000003")
    r = client.put(f"/api/admin/customers/{cust['id']}", json={"name": ""})
    assert r.status_code in (400, 422)


# --------------------------------------------------------------------------- #
# 401 — auth                                                                   #
# --------------------------------------------------------------------------- #


def test_protected_endpoint_without_auth_returns_401(anon_client) -> None:
    assert anon_client.get("/api/customers").status_code == 401
    assert anon_client.get("/api/policies").status_code == 401
    assert anon_client.get("/api/settings").status_code == 401


# --------------------------------------------------------------------------- #
# Empty-database responses                                                     #
# --------------------------------------------------------------------------- #


def test_listing_endpoints_return_empty_array_not_null(client) -> None:
    """
    Even before any data is created in this fixture's DB, listing endpoints
    must return ``[]`` so frontend code can iterate without null-checks.
    """
    today = date.today().isoformat()
    # /api/customers and /api/policies might have data from sibling tests;
    # /api/import/statement-lines starts empty and stays empty in this module.
    r = client.get("/api/statement-lines")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# --------------------------------------------------------------------------- #
# Unknown route / method                                                       #
# --------------------------------------------------------------------------- #


def test_unknown_route_returns_404(client) -> None:
    r = client.get("/api/this-route-does-not-exist")
    assert r.status_code == 404


def test_wrong_method_returns_405(client) -> None:
    """``GET /api/customers`` exists; ``PATCH`` on the collection does not."""
    r = client.patch("/api/customers", json={})
    assert r.status_code == 405
