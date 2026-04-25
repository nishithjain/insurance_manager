"""
Authentication-layer tests using the shared ``app_env`` fixture.

This file complements the deeper coverage already in ``test_auth_and_admin.py``
(which exercises admin CRUD and dev-login). Here we focus on the core gating
behaviours requested by the spec:

- Protected APIs reject unauthenticated requests (401)
- Public APIs do *not* require auth
- Admin-only APIs reject non-admin users (403)
- Admin-only APIs admit admin users (200)

These tests intentionally mint tokens with the project's real
``domain.security.create_access_token`` helper so the JWT format and signing
key path go through production code.
"""

from __future__ import annotations


def test_protected_endpoint_rejects_missing_auth(anon_client) -> None:
    r = anon_client.get("/api/customers")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_protected_endpoint_rejects_malformed_bearer(anon_client) -> None:
    anon_client.headers["Authorization"] = "Bearer not.a.valid.jwt.at.all"
    try:
        r = anon_client.get("/api/customers")
        assert r.status_code == 401
    finally:
        anon_client.headers.pop("Authorization", None)


def test_protected_endpoint_rejects_non_bearer_scheme(anon_client) -> None:
    anon_client.headers["Authorization"] = "Basic Zm9vOmJhcg=="
    try:
        r = anon_client.get("/api/customers")
        assert r.status_code == 401
    finally:
        anon_client.headers.pop("Authorization", None)


def test_public_endpoints_do_not_require_auth(anon_client) -> None:
    assert anon_client.get("/api/").status_code == 200
    assert anon_client.get("/api/health").status_code == 200
    # Public root site landing.
    assert anon_client.get("/").status_code == 200


def test_admin_endpoints_admit_admin(client) -> None:
    r = client.get("/api/users")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)


def test_admin_endpoints_reject_non_admin(client, app_env) -> None:
    """
    Provision a regular user via the admin endpoint and mint a token bound to
    that row. ``require_admin`` reads the role from the DB row (not the JWT
    claim), so the only way to assert the 403 is via a real ``role='user'`` row.
    """
    created = client.post(
        "/api/users",
        json={
            # Pydantic's email validator rejects ``.local`` as a reserved TLD,
            # so we use a regular ``example.com`` address here.
            "email": "non.admin@example.com",
            "full_name": "Non Admin",
            "role": "user",
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    user = created.json()

    user_token = app_env["sign"](user["id"], user["email"], "user")
    c = app_env["client"]
    saved = c.headers.get("Authorization")
    c.headers["Authorization"] = f"Bearer {user_token}"
    try:
        r = c.get("/api/users")
        assert r.status_code == 403
        assert "administrator" in r.json()["detail"].lower()
    finally:
        if saved is not None:
            c.headers["Authorization"] = saved


def test_auth_me_returns_current_principal(client, app_env) -> None:
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == app_env["admin_email"]
    assert body["role"] == "admin"
    assert body["is_active"] is True
