"""
Shared pytest fixtures for the backend test suite.

Why a custom bootstrap?
-----------------------
The backend resolves its SQLite path **at import time** in :mod:`db_path`,
which means any fixture that wants to point the app at a temp database has to:

1. Set ``INSURANCE_DB_PATH`` *before* the first ``import server``, and
2. Drop any cached backend modules from ``sys.modules`` so the next import
   re-evaluates ``DB_PATH``.

This file centralizes that recipe so individual test modules don't have to
re-implement it. Two existing test files (``test_api_smoke.py`` and
``test_auth_and_admin.py``) bootstrap themselves directly — they keep working
because the helper here is opt-in (you have to ``request`` the fixture).

Scope choice
------------
``app_env`` is **module-scoped** on purpose. Per-test-function bootstrap is
prohibitively slow (full module reload + ``init_db`` every test) and the
tests we add are written to be order-independent within a module by using
unique customer/policy names instead of clean-slate-per-test.

Environment isolation
---------------------
Every bootstrap call writes to its own ``tmp_path`` SQLite file and removes
the file on teardown. We also stash and restore the env vars we touch so the
test process exits clean.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable, Iterator, TypedDict

import pytest
from fastapi.testclient import TestClient


# Module names we own that must be re-imported after we change INSURANCE_DB_PATH.
# ``db_path.DB_PATH`` is computed once at import; keeping a stale module would
# silently route every test through the previous fixture's database.
_BACKEND_MODULES_TO_RELOAD = {
    "server",
    "deps",
    "database",
    "db_path",
    "schemas",
    "routers",
    "repositories",
    "domain",
    "services",
    # Top-level modules imported transitively by routers/services that hold
    # cached references to ``database.get_db`` / ``db_path.DB_PATH``. Without
    # flushing them, the next test module's bootstrap would re-bind ``database``
    # to a fresh tempfile, but these helpers would still talk to the previous
    # (now-deleted) DB file.
    "insurance_statistics",
    "policy_export",
    "statement_materialize",
    "statement_parse",
}


def _flush_backend_modules() -> None:
    for mod_name in list(sys.modules):
        head = mod_name.split(".", 1)[0]
        if head in _BACKEND_MODULES_TO_RELOAD:
            del sys.modules[mod_name]


class AppEnv(TypedDict):
    """Bundle returned by the ``app_env`` fixture."""

    client: TestClient
    db_path: str
    admin_id: int
    admin_email: str
    sign: Callable[[int, str, str], str]


def _bootstrap_app(db_path: str, admin_email: str = "admin@test.local") -> AppEnv:
    """
    Stand up a fresh FastAPI app pointed at ``db_path`` and seed an admin row.

    The function signs a JWT for the admin so any caller can put it in an
    ``Authorization: Bearer …`` header and exercise protected endpoints.
    """
    os.environ["INSURANCE_DB_PATH"] = db_path
    os.environ["AUTH_JWT_SECRET"] = "test-jwt-secret-at-least-32-chars-long-x"
    os.environ["INITIAL_ADMIN_EMAIL"] = admin_email
    os.environ["INITIAL_ADMIN_NAME"] = "Test Admin"
    # Make sure no leftover allow-list affects unrelated tests.
    os.environ.pop("ALLOW_DEV_AUTH", None)

    _flush_backend_modules()

    server = importlib.import_module("server")
    security = importlib.import_module("domain.security")
    database_mod = importlib.import_module("database")
    app_users_repo_mod = importlib.import_module("repositories.app_users")

    # ``server.py`` calls ``load_dotenv(..., override=True)`` at import time,
    # which silently replaces our test env vars with whatever is in
    # ``backend/.env``. Re-apply the test values *after* the import so the
    # admin bootstrap below seeds the email we expect, and so JWT signing
    # uses our test secret rather than the one shipped in .env.
    os.environ["INITIAL_ADMIN_EMAIL"] = admin_email
    os.environ["INITIAL_ADMIN_NAME"] = "Test Admin"
    os.environ["AUTH_JWT_SECRET"] = "test-jwt-secret-at-least-32-chars-long-x"
    os.environ.pop("ALLOW_DEV_AUTH", None)
    # ``GOOGLE_CLIENT_ID`` from .env enables a code path in /api/auth/google we
    # don't want firing during unrelated tests; tests that need it set it
    # explicitly themselves.
    os.environ.pop("GOOGLE_CLIENT_ID", None)

    async def _seed_admin():
        import aiosqlite

        await database_mod.init_db()
        db = await aiosqlite.connect(db_path)
        db.row_factory = aiosqlite.Row
        try:
            repo = app_users_repo_mod.AppUserRepository(db)
            admin = await repo.get_by_email(admin_email)
            assert admin is not None, "Admin bootstrap should have seeded INITIAL_ADMIN_EMAIL"
            return admin
        finally:
            await db.close()

    admin = asyncio.run(_seed_admin())

    def sign(user_id: int, email: str, role: str) -> str:
        token, _ = security.create_access_token(user_id=user_id, email=email, role=role)
        return token

    client = TestClient(server.app)
    client.headers["Authorization"] = f"Bearer {sign(admin.id, admin.email, admin.role)}"

    return AppEnv(
        client=client,
        db_path=db_path,
        admin_id=admin.id,
        admin_email=admin.email,
        sign=sign,
    )


# --------------------------------------------------------------------------- #
# Public fixtures                                                             #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def app_env() -> Iterator[AppEnv]:
    """
    Module-scoped FastAPI app + admin-authed ``TestClient`` against a temp DB.

    The fixture yields an :class:`AppEnv` so test modules that need to mint
    additional tokens (e.g. for non-admin role tests) can call ``env["sign"](…)``.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    snapshot = {
        key: os.environ.get(key)
        for key in (
            "INSURANCE_DB_PATH",
            "AUTH_JWT_SECRET",
            "INITIAL_ADMIN_EMAIL",
            "INITIAL_ADMIN_NAME",
            "ALLOW_DEV_AUTH",
            "GOOGLE_CLIENT_ID",
        )
    }

    env = _bootstrap_app(db_path)
    try:
        with env["client"]:
            yield env
    finally:
        try:
            Path(db_path).unlink(missing_ok=True)
        except OSError:
            pass
        for key, value in snapshot.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        # Drop the cached backend modules so the next test module's bootstrap
        # (e.g. ``test_api_smoke.py``) re-imports them against its own
        # ``INSURANCE_DB_PATH``. Without this, modules cached against the
        # already-deleted temp DB can leak into the next module's connections.
        _flush_backend_modules()


@pytest.fixture()
def client(app_env: AppEnv) -> TestClient:
    """Admin-authenticated test client (default for most endpoint tests)."""
    c = app_env["client"]
    c.headers["Authorization"] = f"Bearer {app_env['sign'](app_env['admin_id'], app_env['admin_email'], 'admin')}"
    return c


@pytest.fixture()
def anon_client(app_env: AppEnv) -> Iterator[TestClient]:
    """Unauthenticated client. Restores the admin auth header on teardown."""
    c = app_env["client"]
    saved = c.headers.pop("Authorization", None)
    try:
        yield c
    finally:
        if saved is not None:
            c.headers["Authorization"] = saved


# --------------------------------------------------------------------------- #
# Sample-data builder fixtures                                                #
# --------------------------------------------------------------------------- #


@pytest.fixture()
def make_customer(client: TestClient) -> Callable[..., dict]:
    """
    Factory: ``make_customer(name="Alice", phone="999...")`` → created customer JSON.

    Falls back to unique placeholder values so two calls inside the same test
    module don't collide on any UNIQUE constraint that may exist now or later.
    """
    counter = {"n": 0}

    def _create(
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        address: str | None = None,
    ) -> dict:
        counter["n"] += 1
        n = counter["n"]
        payload = {
            "name": name or f"Test Customer {n}",
            "email": email,
            "phone": phone or f"99999{n:05d}",
            "address": address,
        }
        r = client.post("/api/customers", json=payload)
        assert r.status_code == 200, r.text
        return r.json()

    return _create


@pytest.fixture()
def make_policy(client: TestClient) -> Callable[..., dict]:
    """
    Factory: ``make_policy(customer_id, end_date=…, …)`` → created policy JSON.

    Defaults pick today/today+30 so the row lands inside ``expiring_within_30``
    by default; tests that need other windows pass explicit dates.
    """
    counter = {"n": 0}

    def _create(
        customer_id: str,
        *,
        policy_number: str | None = None,
        policy_type: str = "auto",
        start_date: str | None = None,
        end_date: str | None = None,
        premium: float = 1234.56,
        status: str = "active",
    ) -> dict:
        from datetime import date, timedelta

        counter["n"] += 1
        n = counter["n"]
        payload = {
            "customer_id": customer_id,
            "policy_number": policy_number or f"PT-{n:04d}",
            "policy_type": policy_type,
            "start_date": start_date or date.today().isoformat(),
            "end_date": end_date or (date.today() + timedelta(days=30)).isoformat(),
            "premium": premium,
            "status": status,
        }
        r = client.post("/api/policies", json=payload)
        assert r.status_code == 200, r.text
        return r.json()

    return _create
