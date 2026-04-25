"""
Application-startup smoke tests.

These guarantee the basics that every other test depends on:

- The composition root in :mod:`server` imports without side-effects on the
  real ``insurance.db`` (no implicit DB writes, no env mutation).
- Every router module the app mounts is importable in isolation.
- The lifespan creates the schema tables we depend on.

The first two tests are deliberately ``aiosqlite``-free so they keep working
on Python builds where the async SQLite stack is unstable. The third test
uses the shared ``app_env`` fixture (TestClient + temp DB), which exercises
the full lifespan + ``init_db`` path.
"""

from __future__ import annotations

import importlib
import sqlite3

import pytest


# --------------------------------------------------------------------------- #
# Pure import / structure (no aiosqlite, no DB)                                #
# --------------------------------------------------------------------------- #


def test_server_module_imports_cleanly() -> None:
    """``import server`` must succeed standalone — nothing should require a live DB."""
    server = importlib.import_module("server")
    assert hasattr(server, "app"), "server.app FastAPI instance missing"
    assert server.app.title  # FastAPI gives a default; just confirm the attr is set.


@pytest.mark.parametrize(
    "router_module",
    [
        "routers.app_users",
        "routers.auth",
        "routers.customers",
        "routers.exports",
        "routers.policies",
        "routers.renewals",
        "routers.settings",
        "routers.statements",
        "routers.sync",
        "routers.system",
        "routers.types",
    ],
)
def test_each_router_module_imports(router_module: str) -> None:
    mod = importlib.import_module(router_module)
    assert hasattr(mod, "router"), f"{router_module}.router missing"


def test_expected_routes_are_registered() -> None:
    """
    Quick sanity that the well-known endpoints survived the router split. We
    don't inspect every path — just the high-traffic ones the frontend and
    Android app are known to call.
    """
    server = importlib.import_module("server")
    paths = {route.path for route in server.app.routes}

    expected = {
        "/",
        "/api/",
        "/api/health",
        "/api/customers",
        "/api/customers/{customer_id}",
        "/api/policies",
        "/api/policies/{policy_id}",
        "/api/policies/{policy_id}/contact",
        "/api/policies/{policy_id}/payment",
        "/api/policies/{policy_id}/renewal-resolution",
        "/api/renewals/reminders",
        "/api/renewals/expiring-list",
        "/api/insurance-types",
        "/api/policy-types",
        "/api/settings",
        "/api/auth/google",
        "/api/auth/me",
    }
    missing = expected - paths
    assert not missing, f"Routes missing from app: {missing}"


# --------------------------------------------------------------------------- #
# Lifespan + DB initialization (uses TestClient + temp DB)                     #
# --------------------------------------------------------------------------- #


_EXPECTED_CORE_TABLES = {
    "users",
    "customers",
    "policies",
    "insurance_categories",
    "policy_types",
    "payment_statuses",
    "app_settings",
    "app_users",
    "statement_policy_lines",
}


def test_database_tables_initialize_during_lifespan(app_env) -> None:
    """
    After ``TestClient`` triggers the lifespan, all core tables exist and the
    health endpoint reports counts (possibly zero) for the well-known ones.
    """
    db_path = app_env["db_path"]
    conn = sqlite3.connect(db_path)
    try:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        conn.close()

    missing = _EXPECTED_CORE_TABLES - names
    assert not missing, f"core tables missing after init_db: {missing}"


def test_health_endpoint_reports_initialized_db(client) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["database_exists"] is True
    for key in ("count_users", "count_customers", "count_policies"):
        assert key in body, f"{key} missing from /api/health payload"


def test_root_landing_when_no_frontend_dist(client) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("api_base") == "/api/"
    assert body.get("health") == "/api/health"
