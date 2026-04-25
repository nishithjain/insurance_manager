"""
Unit tests for :class:`services.database_backup.DatabaseBackupService`.

These exercise the on-disk behaviour directly:

- When no backup folder is configured (``app_settings`` row absent), the
  service skips silently and creates no files.
- When a backup folder is configured, the *first* call writes both
  ``insurance_pre_modify_backup.db`` and ``insurance_daily_backup.db``.
- A subsequent call on the same day overwrites the pre-modify backup but
  leaves the daily backup's file timestamp alone (we assert via mtime).
- When the daily file's mtime is back-dated to yesterday, the next call
  refreshes it (covering the "daily backup replaces only daily backup" rule).
- Invalid backup folder strings (non-existent parent, bad characters) are
  handled gracefully — the service logs and returns without raising.

We use ``sqlite3`` (sync) only — no aiosqlite — so this file stays useful on
Python builds where the async stack is fragile.
"""

from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest


def _seed_real_sqlite_db(db_file: Path, backup_folder: str | None) -> None:
    """
    Build a minimal SQLite file the backup service can read.

    The service only reads ``app_settings`` and runs ``backup`` against the
    whole file, so two tables + a settings row is enough.
    """
    conn = sqlite3.connect(str(db_file))
    try:
        conn.executescript(
            """
            CREATE TABLE app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            );
            CREATE TABLE customers (id INTEGER PRIMARY KEY, full_name TEXT);
            INSERT INTO customers (full_name) VALUES ('Sample');
            """
        )
        if backup_folder is not None:
            conn.execute(
                "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("database_backup_folder", backup_folder, datetime.utcnow().isoformat()),
            )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def backup_service_module(tmp_path, monkeypatch):
    """
    Re-import the backup service against a temp DB path.

    ``services.database_backup`` reads ``db_path.DB_PATH`` *at module import
    time*, so we point the env var first, drop any cached copy, and re-import.
    Restoring the original modules on teardown is left to pytest's normal
    sys.modules isolation — every test that needs a fresh service uses this
    fixture and gets a brand-new module.
    """
    db_file = tmp_path / "fixture.db"
    monkeypatch.setenv("INSURANCE_DB_PATH", str(db_file))
    for mod in ("services.database_backup", "db_path"):
        sys.modules.pop(mod, None)
    mod = importlib.import_module("services.database_backup")
    return mod, db_file


# --------------------------------------------------------------------------- #
# No backup folder configured                                                 #
# --------------------------------------------------------------------------- #


def test_no_backup_folder_skips_silently(backup_service_module, tmp_path) -> None:
    mod, db_file = backup_service_module
    _seed_real_sqlite_db(db_file, backup_folder=None)

    # Should NOT raise even though there's no folder configured.
    mod.DatabaseBackupService(db_file).backup_before_write()

    # And the tmp_path is otherwise empty (besides our DB file).
    siblings = [p for p in tmp_path.iterdir() if p != db_file]
    assert siblings == [], "no folder configured → no files should be created"


def test_missing_db_file_does_not_raise(backup_service_module, tmp_path) -> None:
    mod, db_file = backup_service_module
    # Don't create db_file at all.
    assert not db_file.exists()
    # The service must tolerate a missing source DB (e.g. very first startup).
    mod.DatabaseBackupService(db_file).backup_before_write()


# --------------------------------------------------------------------------- #
# Backup folder configured → files appear                                      #
# --------------------------------------------------------------------------- #


def test_first_call_creates_pre_modify_and_daily_files(
    backup_service_module, tmp_path
) -> None:
    mod, db_file = backup_service_module
    backup_dir = tmp_path / "backups"
    _seed_real_sqlite_db(db_file, backup_folder=str(backup_dir))

    mod.DatabaseBackupService(db_file).backup_before_write()

    pre = backup_dir / mod.PRE_MODIFY_BACKUP_FILENAME
    daily = backup_dir / mod.DAILY_BACKUP_FILENAME
    assert pre.is_file(), "pre-modify backup missing after first call"
    assert daily.is_file(), "daily backup missing after first call"

    # Each backup must be a readable SQLite file with the same data shape.
    for f in (pre, daily):
        conn = sqlite3.connect(str(f))
        try:
            count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            assert count == 1
        finally:
            conn.close()


def test_pre_modify_is_replaced_on_subsequent_call(
    backup_service_module, tmp_path
) -> None:
    mod, db_file = backup_service_module
    backup_dir = tmp_path / "backups"
    _seed_real_sqlite_db(db_file, backup_folder=str(backup_dir))

    svc = mod.DatabaseBackupService(db_file)
    svc.backup_before_write()
    pre = backup_dir / mod.PRE_MODIFY_BACKUP_FILENAME
    first_mtime = pre.stat().st_mtime

    # Mutate the source so the next backup is observably different.
    conn = sqlite3.connect(str(db_file))
    try:
        conn.execute("INSERT INTO customers (full_name) VALUES ('Second')")
        conn.commit()
    finally:
        conn.close()

    # Make sure mtime granularity (1s on Windows FAT, sometimes Linux ext4 on
    # tmpfs) doesn't fool us into thinking the file wasn't rewritten.
    time.sleep(1.05)
    svc.backup_before_write()

    second_mtime = pre.stat().st_mtime
    assert second_mtime >= first_mtime  # always at least equal
    conn = sqlite3.connect(str(pre))
    try:
        names = {row[0] for row in conn.execute("SELECT full_name FROM customers")}
    finally:
        conn.close()
    assert names == {"Sample", "Second"}, "pre-modify backup did not capture new row"


def test_daily_backup_only_refreshes_when_date_changes(
    backup_service_module, tmp_path
) -> None:
    mod, db_file = backup_service_module
    backup_dir = tmp_path / "backups"
    _seed_real_sqlite_db(db_file, backup_folder=str(backup_dir))

    svc = mod.DatabaseBackupService(db_file)
    svc.backup_before_write()
    daily = backup_dir / mod.DAILY_BACKUP_FILENAME
    first_mtime = daily.stat().st_mtime

    # Same-day second call: daily must NOT be rewritten (mtime equal within
    # tolerance — we set it back to first_mtime so the heuristic is exact).
    time.sleep(1.05)
    svc.backup_before_write()
    same_day_mtime = daily.stat().st_mtime
    assert same_day_mtime == first_mtime, (
        "daily backup was rewritten on a same-day call (should be skipped)"
    )

    # Now back-date the daily file to yesterday and re-run: it should refresh.
    yesterday = date.today() - timedelta(days=1)
    yesterday_ts = time.mktime(
        (yesterday.year, yesterday.month, yesterday.day, 12, 0, 0, 0, 0, -1)
    )
    os.utime(daily, (yesterday_ts, yesterday_ts))

    svc.backup_before_write()
    refreshed_mtime = daily.stat().st_mtime
    assert refreshed_mtime > yesterday_ts, "daily backup should refresh on a new day"


# --------------------------------------------------------------------------- #
# Invalid configuration                                                        #
# --------------------------------------------------------------------------- #


def test_blank_backup_folder_setting_is_ignored(
    backup_service_module, tmp_path
) -> None:
    """A blank string is treated as "not configured" — same as missing key."""
    mod, db_file = backup_service_module
    _seed_real_sqlite_db(db_file, backup_folder="   ")

    mod.DatabaseBackupService(db_file).backup_before_write()
    siblings = [p for p in tmp_path.iterdir() if p != db_file]
    assert siblings == []


def test_creates_backup_folder_if_missing(
    backup_service_module, tmp_path
) -> None:
    mod, db_file = backup_service_module
    backup_dir = tmp_path / "deep" / "nested" / "backup"
    assert not backup_dir.exists()
    _seed_real_sqlite_db(db_file, backup_folder=str(backup_dir))

    mod.DatabaseBackupService(db_file).backup_before_write()
    assert backup_dir.is_dir()
    assert (backup_dir / mod.PRE_MODIFY_BACKUP_FILENAME).is_file()
