"""
Tests for the ``/api/settings`` endpoint pair.

The settings router currently exposes a single key — ``database_backup_folder``
— but is structured so future keys plug into the same ``app_settings`` table.
We assert the existing contract:

- A fresh DB returns ``database_backup_folder = None``.
- ``PUT /api/settings`` with a value persists and is round-trippable through
  ``GET /api/settings``.
- A second ``PUT`` with a different value overwrites the first.
- ``PUT`` with empty string / None / whitespace clears the row again
  (``GET`` then returns ``None``).
- The persisted value is reachable via the same ``app_settings`` row that the
  :class:`DatabaseBackupService` reads, confirming the two layers agree on the
  storage location.
- Endpoints require auth (covered for completeness).
"""

from __future__ import annotations

import sqlite3


def _read_setting_directly(db_path: str) -> str | None:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            ("database_backup_folder",),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def test_get_settings_starts_unconfigured(client) -> None:
    r = client.get("/api/settings")
    assert r.status_code == 200
    body = r.json()
    assert body == {"database_backup_folder": None}


def test_put_settings_persists_and_round_trips(client, app_env, tmp_path) -> None:
    folder = str(tmp_path / "first-folder")
    r = client.put("/api/settings", json={"database_backup_folder": folder})
    assert r.status_code == 200
    assert r.json() == {"database_backup_folder": folder}

    r = client.get("/api/settings")
    assert r.json() == {"database_backup_folder": folder}

    # Backup-service-side read must see the same value (this is the row the
    # service consults at backup time).
    assert _read_setting_directly(app_env["db_path"]) == folder


def test_put_settings_replaces_prior_value(client, tmp_path) -> None:
    a = str(tmp_path / "alpha-folder")
    b = str(tmp_path / "beta-folder")
    client.put("/api/settings", json={"database_backup_folder": a})
    r = client.put("/api/settings", json={"database_backup_folder": b})
    assert r.status_code == 200
    assert r.json() == {"database_backup_folder": b}
    assert client.get("/api/settings").json() == {"database_backup_folder": b}


def test_put_settings_clears_on_empty_string(client, app_env, tmp_path) -> None:
    folder = str(tmp_path / "to-be-cleared")
    client.put("/api/settings", json={"database_backup_folder": folder})

    r = client.put("/api/settings", json={"database_backup_folder": ""})
    assert r.status_code == 200
    assert r.json() == {"database_backup_folder": None}
    assert client.get("/api/settings").json() == {"database_backup_folder": None}
    assert _read_setting_directly(app_env["db_path"]) is None


def test_put_settings_clears_on_whitespace_only(client, tmp_path) -> None:
    """``  ``-only values must be treated as "clear" (current router behaviour)."""
    folder = str(tmp_path / "ws-cleared")
    client.put("/api/settings", json={"database_backup_folder": folder})

    r = client.put("/api/settings", json={"database_backup_folder": "   "})
    assert r.status_code == 200
    assert r.json() == {"database_backup_folder": None}


def test_put_settings_clears_on_null(client, tmp_path) -> None:
    folder = str(tmp_path / "null-cleared")
    client.put("/api/settings", json={"database_backup_folder": folder})

    r = client.put("/api/settings", json={"database_backup_folder": None})
    assert r.status_code == 200
    assert r.json() == {"database_backup_folder": None}


def test_settings_endpoints_require_auth(anon_client) -> None:
    assert anon_client.get("/api/settings").status_code == 401
    assert anon_client.put(
        "/api/settings", json={"database_backup_folder": "x"}
    ).status_code == 401
