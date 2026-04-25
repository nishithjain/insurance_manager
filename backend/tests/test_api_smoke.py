"""
End-to-end smoke tests for the refactored HTTP layer.

These exercise the full DI graph (lifespan → init_db → ``get_db`` →
``get_current_user`` → router) against a fresh temporary SQLite file, so every
router module, schema, and domain helper is covered.

Critically, the DB path must be set **before** any backend module is imported,
because ``db_path.py`` freezes ``DB_PATH`` at import time. We do that via the
``INSURANCE_DB_PATH`` environment variable in an autouse fixture.
"""

from __future__ import annotations

import importlib
import io
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """
    Spin up the app against a fresh temp SQLite file and authenticate the client
    as an admin so every protected endpoint is reachable.

    We can't go through POST /api/auth/google here (that would require a real
    Google ID token), so the fixture seeds an admin row directly via the
    repository and mints a backend JWT through the same helper the login flow
    uses. This exercises ``get_current_principal`` and ``require_admin`` on
    every request, which is what we want to test.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name
    os.environ["INSURANCE_DB_PATH"] = db_path
    os.environ["AUTH_JWT_SECRET"] = "test-only-jwt-secret-at-least-32-chars-long"
    os.environ["INITIAL_ADMIN_EMAIL"] = "admin@test.local"
    os.environ["INITIAL_ADMIN_NAME"] = "Test Admin"

    # Flush *all* cached backend modules including submodules so
    # ``database.connection`` re-evaluates ``DB_PATH`` from the new env var.
    _backend_roots = {
        "server",
        "deps",
        "database",
        "db_path",
        "schemas",
        "routers",
        "repositories",
        "domain",
        "services",
    }
    for mod_name in list(sys.modules):
        if mod_name.split(".", 1)[0] in _backend_roots:
            del sys.modules[mod_name]

    server = importlib.import_module("server")
    security = importlib.import_module("domain.security")
    app_users_repo_mod = importlib.import_module("repositories.app_users")
    database_mod = importlib.import_module("database")

    # ``server.py`` calls ``load_dotenv(.., override=True)`` at import time
    # which overwrites our test env vars with ``backend/.env`` values.
    # Re-apply the test values so admin seeding & JWT signing use them.
    os.environ["INITIAL_ADMIN_EMAIL"] = "admin@test.local"
    os.environ["INITIAL_ADMIN_NAME"] = "Test Admin"
    os.environ["AUTH_JWT_SECRET"] = "test-only-jwt-secret-at-least-32-chars-long"

    import asyncio

    async def _seed_and_sign() -> str:
        import aiosqlite

        await database_mod.init_db()
        db = await aiosqlite.connect(db_path)
        db.row_factory = aiosqlite.Row
        try:
            repo = app_users_repo_mod.AppUserRepository(db)
            admin = await repo.get_by_email("admin@test.local")
            assert admin is not None, "INITIAL_ADMIN_EMAIL bootstrap should have seeded admin"
            token, _exp = security.create_access_token(
                user_id=admin.id, email=admin.email, role=admin.role
            )
            return token
        finally:
            await db.close()

    token = asyncio.run(_seed_and_sign())

    with TestClient(server.app) as c:
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c

    try:
        os.unlink(db_path)
    except OSError:
        pass
    for key in ("INSURANCE_DB_PATH", "AUTH_JWT_SECRET", "INITIAL_ADMIN_EMAIL", "INITIAL_ADMIN_NAME"):
        os.environ.pop(key, None)


# --------------------------------------------------------------------------- #
# System / root                                                               #
# --------------------------------------------------------------------------- #


def test_site_root(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["api_base"] == "/api/"
    assert body["health"] == "/api/health"


def test_api_root(client: TestClient) -> None:
    r = client.get("/api/")
    assert r.status_code == 200
    assert r.json()["message"] == "Insurance App API"


def test_health(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["database_exists"] is True
    # Row counts for core tables should be present (possibly 0).
    assert "count_users" in body
    assert "count_customers" in body
    assert "count_policies" in body


# --------------------------------------------------------------------------- #
# Customers                                                                    #
# --------------------------------------------------------------------------- #


def test_customers_crud(client: TestClient) -> None:
    r = client.get("/api/customers")
    assert r.status_code == 200
    assert r.json() == []

    r = client.post(
        "/api/customers",
        json={
            "name": "Alice Test",
            "email": "alice@example.com",
            "phone": "9999911111",
            "address": "Line 1, City",
        },
    )
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["name"] == "Alice Test"
    assert created["email"] == "alice@example.com"
    assert created["phone"] == "9999911111"
    assert created["address"] == "Line 1, City"
    cid = created["id"]

    r = client.get(f"/api/customers/{cid}")
    assert r.status_code == 200
    assert r.json()["id"] == cid

    r = client.put(
        f"/api/customers/{cid}",
        json={
            "name": "Alice Renamed",
            "email": "alice2@example.com",
            "phone": "9999922222",
            "address": "Line 2, City",
        },
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["name"] == "Alice Renamed"
    assert updated["phone"] == "9999922222"
    assert updated["address"] == "Line 2, City"

    r = client.get("/api/customers")
    assert r.status_code == 200
    listing = r.json()
    assert len(listing) == 1 and listing[0]["id"] == cid


def test_customer_not_found_is_404(client: TestClient) -> None:
    r = client.get("/api/customers/999999")
    assert r.status_code == 404
    r = client.get("/api/customers/not-a-number")
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# Policies                                                                     #
# --------------------------------------------------------------------------- #


def _create_customer(client: TestClient, name: str = "Bob") -> str:
    r = client.post(
        "/api/customers",
        json={"name": name, "email": None, "phone": "1234567890", "address": None},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _today_iso() -> str:
    return date.today().isoformat()


def _days_ahead(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def test_policies_crud_and_patch_workflows(client: TestClient) -> None:
    cid = _create_customer(client, "Bob Policy")

    r = client.post(
        "/api/policies",
        json={
            "customer_id": cid,
            "policy_number": "P-TEST-001",
            "policy_type": "auto",
            "start_date": _today_iso(),
            "end_date": _days_ahead(20),
            "premium": 12345.67,
            "status": "active",
        },
    )
    assert r.status_code == 200, r.text
    p = r.json()
    pid = p["id"]
    assert p["policy_number"] == "P-TEST-001"
    assert p["status"] == "active"
    assert p["contact_status"] == "Not Contacted"
    assert p["renewal_status"] == "Open"

    r = client.get(f"/api/policies/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid

    r = client.get(f"/api/policies/{pid}/detail")
    assert r.status_code == 200, r.text
    bundle = r.json()
    assert bundle["policy"]["id"] == pid
    assert bundle["customer"]["id"] == cid
    # Auto → Private Car → Motor category; motor row inserted empty at create-time.
    assert bundle["category_group"] == "Motor"
    assert bundle["motor"] is not None
    assert bundle["health"] is None
    assert bundle["property_detail"] is None

    # Contact PATCH.
    r = client.patch(
        f"/api/policies/{pid}/contact",
        json={
            "contact_status": "Contacted Today",
            "last_contacted_at": _today_iso(),
            "follow_up_date": _days_ahead(3),
        },
    )
    assert r.status_code == 200
    assert r.json()["contact_status"] == "Contacted Today"

    # Contact PATCH validation.
    r = client.patch(
        f"/api/policies/{pid}/contact",
        json={"contact_status": "BogusValue"},
    )
    assert r.status_code == 400

    # Renewal resolution PATCH.
    r = client.patch(
        f"/api/policies/{pid}/renewal-resolution",
        json={"renewal_status": "RenewedWithUs", "renewal_resolution_note": "done"},
    )
    assert r.status_code == 200
    assert r.json()["renewal_status"] == "RenewedWithUs"

    r = client.patch(
        f"/api/policies/{pid}/renewal-resolution",
        json={"renewal_status": "Open"},
    )
    assert r.status_code == 200
    assert r.json()["renewal_status"] == "Open"

    # Renewal resolution PATCH validation.
    r = client.patch(
        f"/api/policies/{pid}/renewal-resolution",
        json={"renewal_status": "NotAnEnumValue"},
    )
    assert r.status_code == 400

    # Payment PATCH: default payment status is "Unknown" (seeded). This is NOT
    # PENDING, so the PATCH should be rejected per the documented workflow.
    r = client.patch(
        f"/api/policies/{pid}/payment",
        json={"payment_status": "CUSTOMER ONLINE"},
    )
    assert r.status_code == 400
    assert "PENDING" in r.json()["detail"]

    # Payment PATCH also validates the label itself.
    r = client.patch(
        f"/api/policies/{pid}/payment",
        json={"payment_status": "NOT_A_CHANNEL"},
    )
    assert r.status_code == 400

    # PUT policy (update fields).
    r = client.put(
        f"/api/policies/{pid}",
        json={
            "customer_id": cid,
            "policy_number": "P-TEST-001-v2",
            "policy_type": "auto",
            "start_date": _today_iso(),
            "end_date": _days_ahead(10),
            "premium": 99999.99,
            "status": "active",
        },
    )
    assert r.status_code == 200
    assert r.json()["policy_number"] == "P-TEST-001-v2"
    assert r.json()["premium"] == 99999.99

    # List contains the policy.
    r = client.get("/api/policies")
    assert r.status_code == 200
    listing = r.json()
    assert any(item["id"] == pid for item in listing)


def test_policy_not_found(client: TestClient) -> None:
    r = client.get("/api/policies/999999")
    assert r.status_code == 404
    r = client.get("/api/policies/not-a-number")
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# Renewals (bucketing + expiring-list)                                         #
# --------------------------------------------------------------------------- #


def test_renewal_reminders_and_expiring_list(client: TestClient) -> None:
    # The policy from the previous test expires at today+10, so it should show
    # up in the "30-day" and "15-day" expiring windows, not "today" or "7-day".
    r = client.get("/api/renewals/reminders")
    assert r.status_code == 200
    body = r.json()
    assert set(body["summary"].keys()) == {
        "expiring_today",
        "expiring_within_7_days",
        "expiring_within_15_days",
        "expiring_within_30_days",
        "expiring_within_365_days",
        "expired",
    }
    assert body["summary"]["expiring_within_15_days"] >= 1
    assert body["summary"]["expiring_within_30_days"] >= 1
    assert body["summary"]["expiring_within_365_days"] >= 1
    assert body["summary"]["expiring_today"] == 0

    for window in ("today", "7", "15", "30", "expired"):
        r = client.get("/api/renewals/expiring-list", params={"window": window})
        assert r.status_code == 200, f"{window}: {r.text}"
        assert isinstance(r.json(), list)

    r = client.get("/api/renewals/expiring-list", params={"window": "15"})
    window_15 = r.json()
    assert len(window_15) >= 1
    row = window_15[0]
    assert {"id", "policy_number", "end_date", "policy_type", "days_left"} <= row.keys()

    # Pattern validator should reject bogus windows.
    r = client.get("/api/renewals/expiring-list", params={"window": "nope"})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# Statistics / sync / statement-lines                                          #
# --------------------------------------------------------------------------- #


def test_statistics_dashboard(client: TestClient) -> None:
    r = client.get("/api/statistics/dashboard")
    assert r.status_code == 200, r.text
    body = r.json()
    # Shape must remain identical so the mobile DashboardStatisticsDto keeps parsing.
    required_keys = {
        "payment_received_this_month",
        "pending_payments_count",
        "pending_payments_amount",
        "renewals_this_month",
        "expiring_this_month",
        "renewal_conversion_rate",
        "expired_not_renewed_open",
        "total_customers",
        "repeat_customers",
        "monthly_trend",
        "policy_type_distribution",
        "as_of_date",
        "current_month_label",
    }
    assert required_keys <= body.keys()
    assert body["total_customers"] >= 1


def test_sync_snapshot_and_status(client: TestClient) -> None:
    r = client.post("/api/sync/generate-snapshot")
    assert r.status_code == 200, r.text
    snap = r.json()
    assert snap["schema"] == "normalized_v2"
    assert isinstance(snap["customers"], list) and len(snap["customers"]) >= 1
    assert isinstance(snap["policies"], list) and len(snap["policies"]) >= 1

    r = client.get("/api/sync/status")
    assert r.status_code == 200
    body = r.json()
    # Either "never_synced" or a sync_info row — both are valid.
    assert "last_sync" in body or "status" in body or "id" in body


def test_statement_lines_endpoints(client: TestClient) -> None:
    r = client.get("/api/import/statement-lines/summary")
    assert r.status_code == 200
    assert r.json() == {"statement_rows": 0}

    r = client.get("/api/statement-lines")
    assert r.status_code == 200
    assert r.json() == []


# --------------------------------------------------------------------------- #
# Exports (CSV / ZIP)                                                          #
# --------------------------------------------------------------------------- #


def test_export_policies_csv(client: TestClient) -> None:
    today = date.today()
    r = client.get(
        "/api/export/policies-csv",
        params={"year": today.year, "month": today.month, "by": "policy_end_date"},
    )
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers["content-type"]
    assert r.headers["content-disposition"].startswith("attachment;")
    # UTF-8 BOM preserved.
    assert r.content.startswith(b"\xef\xbb\xbf")

    r = client.get(
        "/api/export/policies-csv",
        params={"year": today.year, "month": today.month, "by": "bogus_column"},
    )
    assert r.status_code == 400


def test_export_full_data_zip(client: TestClient) -> None:
    r = client.get("/api/export/full-data-zip")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"

    import zipfile

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = set(zf.namelist())
    expected = {
        "customers.csv",
        "customer_addresses.csv",
        "policies.csv",
        "motor_export.csv",
        "health_export.csv",
        "non_motor_export.csv",
        "renewal_history.csv",
        "statement_policy_lines.csv",
        "README.txt",
    }
    assert expected <= names, f"missing: {expected - names}"


# --------------------------------------------------------------------------- #
# Deletion (runs last so earlier tests see the customer/policy)                #
# --------------------------------------------------------------------------- #


def test_zz_delete_policy_and_customer(client: TestClient) -> None:
    """
    Delete the seeded rows last; named ``zz_`` so pytest's alphabetical collation
    within the module runs it after every other test. Keeps earlier tests able
    to read the seeded data.
    """
    r = client.get("/api/policies")
    policies = r.json()
    assert policies, "expected at least one policy from earlier tests"
    pid = policies[0]["id"]

    r = client.delete(f"/api/policies/{pid}")
    assert r.status_code == 200
    assert r.json()["message"] == "Policy deleted successfully"

    r = client.get(f"/api/policies/{pid}")
    assert r.status_code == 404

    r = client.get("/api/customers")
    customers = r.json()
    assert customers
    cid = customers[0]["id"]
    r = client.delete(f"/api/customers/{cid}")
    assert r.status_code == 200
    assert r.json()["message"] == "Customer deleted successfully"
