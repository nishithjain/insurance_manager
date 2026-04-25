"""
Auth + admin-user-management tests.

We never call ``POST /api/auth/google`` with a real ID token (no network, no
Google credentials in CI). Instead we:

- Seed an admin row directly via the repository.
- Mint a backend JWT via ``domain.security.create_access_token`` — the same
  helper the production login flow uses.
- Drive every protected endpoint through the normal ``TestClient`` surface,
  so ``get_current_principal`` and ``require_admin`` are exercised end to end.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile
from typing import Callable, Iterator

import pytest
from fastapi.testclient import TestClient


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def app_bundle() -> Iterator[dict]:
    """
    Bring up the app against a temp DB. Yields a dict with:

      - ``client``  : TestClient (no default Authorization header).
      - ``admin``   : seeded admin :class:`AppUserRow`.
      - ``sign``    : function(user_id, email, role) -> JWT string.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name
    os.environ["INSURANCE_DB_PATH"] = db_path
    os.environ["AUTH_JWT_SECRET"] = "test-jwt-secret-at-least-32-chars-long-x"
    os.environ["INITIAL_ADMIN_EMAIL"] = "root@test.local"
    os.environ["INITIAL_ADMIN_NAME"] = "Root Admin"

    # Flush *all* cached backend modules including submodules. Just deleting
    # ``database`` doesn't drop ``database.connection``, which would keep a
    # stale ``DB_PATH`` from a previous test module's bootstrap and route
    # ``init_db()`` to the wrong file ("no such table: app_users").
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
    database_mod = importlib.import_module("database")
    app_users_repo_mod = importlib.import_module("repositories.app_users")

    # ``server.py`` calls ``load_dotenv(.., override=True)`` at import time
    # which overwrites our test env vars with ``backend/.env`` values.
    # Re-apply the test values so admin seeding & JWT signing use them.
    os.environ["INITIAL_ADMIN_EMAIL"] = "root@test.local"
    os.environ["INITIAL_ADMIN_NAME"] = "Root Admin"
    os.environ["AUTH_JWT_SECRET"] = "test-jwt-secret-at-least-32-chars-long-x"

    async def _seed_admin():
        import aiosqlite

        await database_mod.init_db()
        db = await aiosqlite.connect(db_path)
        db.row_factory = aiosqlite.Row
        try:
            repo = app_users_repo_mod.AppUserRepository(db)
            admin = await repo.get_by_email("root@test.local")
            assert admin is not None
            return admin
        finally:
            await db.close()

    admin_row = asyncio.run(_seed_admin())

    def sign(user_id: int, email: str, role: str) -> str:
        token, _ = security.create_access_token(user_id=user_id, email=email, role=role)
        return token

    with TestClient(server.app) as c:
        yield {"client": c, "admin": admin_row, "sign": sign}

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture()
def admin_client(app_bundle) -> TestClient:
    c = app_bundle["client"]
    admin = app_bundle["admin"]
    sign: Callable = app_bundle["sign"]
    c.headers.pop("Authorization", None)
    c.headers["Authorization"] = f"Bearer {sign(admin.id, admin.email, admin.role)}"
    return c


@pytest.fixture()
def anon_client(app_bundle) -> TestClient:
    c = app_bundle["client"]
    c.headers.pop("Authorization", None)
    return c


# --------------------------------------------------------------------------- #
# 401/403 gating                                                              #
# --------------------------------------------------------------------------- #


def test_protected_endpoint_requires_auth(anon_client: TestClient) -> None:
    r = anon_client.get("/api/customers")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_public_endpoints_do_not_require_auth(anon_client: TestClient) -> None:
    assert anon_client.get("/api/health").status_code == 200
    assert anon_client.get("/api/").status_code == 200
    # /auth/login with a bad token is 401, not 403 → still "public" in routing sense.
    r = anon_client.post("/api/auth/google", json={"id_token": "not-a-real-token"})
    assert r.status_code in (401, 503)


def test_invalid_bearer_is_rejected(anon_client: TestClient) -> None:
    anon_client.headers["Authorization"] = "Bearer clearly.not.a.jwt"
    r = anon_client.get("/api/auth/me")
    assert r.status_code == 401


def test_non_admin_cannot_hit_admin_endpoints(app_bundle) -> None:
    """A valid JWT with role=user still can't manage users."""
    c = app_bundle["client"]
    sign = app_bundle["sign"]
    # A user row doesn't even need to exist in the DB for the role check itself
    # (the JWT carries the role), but the principal dep also verifies the row
    # still exists, so we need a real row. Seed one via the admin.
    admin_token = sign(app_bundle["admin"].id, app_bundle["admin"].email, "admin")
    c.headers["Authorization"] = f"Bearer {admin_token}"
    created = c.post(
        "/api/users",
        json={
            "email": "regular@example.com",
            "full_name": "Regular User",
            "role": "user",
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    uid = created.json()["id"]

    user_token = sign(uid, "regular@example.com", "user")
    c.headers["Authorization"] = f"Bearer {user_token}"
    r = c.get("/api/users")
    assert r.status_code == 403

    # …but they *can* hit protected-but-not-admin endpoints.
    r = c.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["role"] == "user"


# --------------------------------------------------------------------------- #
# Admin CRUD                                                                   #
# --------------------------------------------------------------------------- #


def test_admin_can_list_and_create_users(admin_client: TestClient) -> None:
    r = admin_client.get("/api/users")
    assert r.status_code == 200
    emails_before = {u["email"] for u in r.json()}

    r = admin_client.post(
        "/api/users",
        json={
            "email": "Alice.New@Example.Com",
            "full_name": "Alice New",
            "role": "user",
            "is_active": True,
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["email"] == "alice.new@example.com", "email should be canonicalized lowercase"
    assert created["role"] == "user"
    assert created["is_active"] is True
    assert created["created_by"] is not None

    r = admin_client.get("/api/users")
    emails_after = {u["email"] for u in r.json()}
    assert emails_after - emails_before == {"alice.new@example.com"}


def test_create_user_rejects_duplicate_email(admin_client: TestClient) -> None:
    admin_client.post(
        "/api/users",
        json={
            "email": "bob@example.com",
            "full_name": "Bob",
            "role": "user",
            "is_active": True,
        },
    )
    r = admin_client.post(
        "/api/users",
        json={
            "email": "BOB@EXAMPLE.COM",
            "full_name": "Bob Dup",
            "role": "user",
            "is_active": True,
        },
    )
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_create_user_rejects_invalid_role(admin_client: TestClient) -> None:
    r = admin_client.post(
        "/api/users",
        json={
            "email": "weird@example.com",
            "full_name": "Weird",
            "role": "superadmin",
            "is_active": True,
        },
    )
    assert r.status_code == 400
    assert "role" in r.json()["detail"].lower()


def test_edit_user_and_toggle_status(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/users",
        json={
            "email": "carol@example.com",
            "full_name": "Carol",
            "role": "user",
            "is_active": True,
        },
    ).json()
    uid = created["id"]

    r = admin_client.put(
        f"/api/users/{uid}",
        json={"full_name": "Carol Renamed", "role": "user", "is_active": True},
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Carol Renamed"

    r = admin_client.put(f"/api/users/{uid}/status", json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    r = admin_client.put(f"/api/users/{uid}/status", json={"is_active": True})
    assert r.status_code == 200
    assert r.json()["is_active"] is True


def test_disabled_user_cannot_call_protected_endpoint(app_bundle, admin_client: TestClient) -> None:
    """Even a valid JWT won't work once the admin deactivates the account."""
    created = admin_client.post(
        "/api/users",
        json={
            "email": "darren@example.com",
            "full_name": "Darren",
            "role": "user",
            "is_active": True,
        },
    ).json()
    uid = created["id"]

    token = app_bundle["sign"](uid, "darren@example.com", "user")
    c = app_bundle["client"]
    c.headers["Authorization"] = f"Bearer {token}"
    assert c.get("/api/auth/me").status_code == 200

    # Admin deactivates.
    admin = app_bundle["admin"]
    admin_token = app_bundle["sign"](admin.id, admin.email, admin.role)
    c.headers["Authorization"] = f"Bearer {admin_token}"
    admin_client.put(f"/api/users/{uid}/status", json={"is_active": False})

    c.headers["Authorization"] = f"Bearer {token}"
    r = c.get("/api/auth/me")
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"].lower()


def test_cannot_demote_or_delete_last_active_admin(admin_client: TestClient, app_bundle) -> None:
    admin_id = app_bundle["admin"].id
    r = admin_client.put(
        f"/api/users/{admin_id}",
        json={"role": "user"},
    )
    assert r.status_code == 409
    assert "last active admin" in r.json()["detail"].lower()

    r = admin_client.put(f"/api/users/{admin_id}/status", json={"is_active": False})
    assert r.status_code == 409

    r = admin_client.delete(f"/api/users/{admin_id}")
    assert r.status_code == 409


def test_search_filter(admin_client: TestClient) -> None:
    admin_client.post(
        "/api/users",
        json={
            "email": "searchable.needle@example.com",
            "full_name": "Searchable Needle",
            "role": "user",
            "is_active": True,
        },
    )
    r = admin_client.get("/api/users", params={"search": "needle"})
    assert r.status_code == 200
    payload = r.json()
    assert any(u["email"] == "searchable.needle@example.com" for u in payload)
    assert all("needle" in (u["email"] + u["full_name"]).lower() for u in payload)


def test_login_rejects_unknown_or_disabled_users(anon_client: TestClient) -> None:
    """Smoke test for the service-level LoginError → 401 mapping."""
    # Without GOOGLE_CLIENT_ID set, the service returns 503. Set it so we can
    # hit the LoginError branch specifically via the (intentional) invalid token.
    os.environ["GOOGLE_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
    try:
        r = anon_client.post("/api/auth/google", json={"id_token": "eyJ-not-a-real-token"})
        assert r.status_code == 401
        assert "rejected" in r.json()["detail"].lower() or "invalid" in r.json()["detail"].lower()
    finally:
        os.environ.pop("GOOGLE_CLIENT_ID", None)


def test_auth_me_returns_current_user(admin_client: TestClient, app_bundle) -> None:
    r = admin_client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == app_bundle["admin"].email
    assert body["role"] == "admin"
    assert body["is_active"] is True


# --------------------------------------------------------------------------- #
# Dev-login (emulator/CI shortcut)                                            #
# --------------------------------------------------------------------------- #


def test_dev_login_404_when_disabled(anon_client: TestClient, app_bundle) -> None:
    """With ALLOW_DEV_AUTH unset, the endpoint must 404 (not even exist)."""
    os.environ.pop("ALLOW_DEV_AUTH", None)
    r = anon_client.post("/api/auth/dev-login", json={"email": app_bundle["admin"].email})
    assert r.status_code == 404


def test_dev_login_issues_token_when_enabled(anon_client: TestClient, app_bundle) -> None:
    os.environ["ALLOW_DEV_AUTH"] = "true"
    try:
        r = anon_client.post(
            "/api/auth/dev-login",
            json={"email": app_bundle["admin"].email},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token_type"] == "Bearer"
        assert body["access_token"]
        assert body["user"]["email"] == app_bundle["admin"].email
        assert body["user"]["role"] == "admin"

        # Returned token should work for a protected call.
        anon_client.headers["Authorization"] = f"Bearer {body['access_token']}"
        me = anon_client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == app_bundle["admin"].email
    finally:
        anon_client.headers.pop("Authorization", None)
        os.environ.pop("ALLOW_DEV_AUTH", None)


def test_dev_login_rejects_unknown_email(anon_client: TestClient) -> None:
    os.environ["ALLOW_DEV_AUTH"] = "true"
    try:
        r = anon_client.post("/api/auth/dev-login", json={"email": "nobody@example.com"})
        assert r.status_code == 401
        assert "not provisioned" in r.json()["detail"].lower()
    finally:
        os.environ.pop("ALLOW_DEV_AUTH", None)


def test_dev_login_rejects_disabled_user(admin_client: TestClient, app_bundle) -> None:
    """A disabled user cannot bypass the allow-list via dev-login either."""
    admin_client.post(
        "/api/users",
        json={
            "email": "dev.disabled@example.com",
            "full_name": "Disabled Dev",
            "role": "user",
            "is_active": False,
        },
    )
    c = app_bundle["client"]
    c.headers.pop("Authorization", None)
    os.environ["ALLOW_DEV_AUTH"] = "true"
    try:
        r = c.post("/api/auth/dev-login", json={"email": "dev.disabled@example.com"})
        assert r.status_code == 401
        assert "disabled" in r.json()["detail"].lower()
    finally:
        os.environ.pop("ALLOW_DEV_AUTH", None)
