"""
Lock down the backup-on-first-write contract of
:class:`database.connection.BackupAioSqliteConnection`.

The connection proxy must fire :meth:`DatabaseBackupService.backup_before_write`
*exactly once* on the first write of a connection's lifetime, and *never*
on read-only statements. Subsequent writes within the same connection
must NOT trigger a second backup (a single connection corresponds to a
single request, and we already snapshotted at the request boundary).

These tests exercise just the regex + the once-flag — they do not touch
``aiosqlite`` so they pass even on the developer's broken ``bmcpython``
build.
"""

from __future__ import annotations

import asyncio
import importlib
from unittest.mock import MagicMock, patch


async def _noop_coro(*_a, **_kw):
    return None


def _new_proxy_with_fake_db() -> tuple[object, MagicMock, MagicMock]:
    """Build a proxy whose underlying aiosqlite connection is a MagicMock.

    ``side_effect`` (rather than ``return_value``) is used so each call
    returns a *fresh* coroutine — otherwise the second await would consume
    an already-driven generator.
    """
    conn = importlib.import_module("database.connection")
    fake_db = MagicMock()
    fake_db.execute = MagicMock(side_effect=lambda *a, **kw: _noop_coro())
    fake_db.executemany = MagicMock(side_effect=lambda *a, **kw: _noop_coro())
    fake_db.executescript = MagicMock(side_effect=lambda *a, **kw: _noop_coro())

    with patch.object(conn, "DatabaseBackupService") as svc_cls:
        backup = MagicMock()
        svc_cls.return_value = backup
        proxy = conn.BackupAioSqliteConnection(fake_db)
    return proxy, fake_db, backup


def _run(coro):
    return asyncio.run(coro)


def test_select_does_not_trigger_backup() -> None:
    proxy, _, backup = _new_proxy_with_fake_db()
    op = proxy.execute("SELECT * FROM customers")
    _run(op._await_operation())
    backup.backup_before_write.assert_not_called()


def test_first_insert_triggers_single_backup() -> None:
    proxy, _, backup = _new_proxy_with_fake_db()
    op = proxy.execute("INSERT INTO customers VALUES (?)", (1,))
    _run(op._await_operation())
    backup.backup_before_write.assert_called_once()


def test_subsequent_writes_in_same_connection_do_not_re_backup() -> None:
    proxy, _, backup = _new_proxy_with_fake_db()
    for sql in (
        "INSERT INTO customers VALUES (1)",
        "UPDATE customers SET name = 'x' WHERE id = 1",
        "DELETE FROM customers WHERE id = 1",
    ):
        op = proxy.execute(sql)
        _run(op._await_operation())
    assert backup.backup_before_write.call_count == 1


def test_executescript_with_leading_comment_is_classified_as_write() -> None:
    """Migration scripts often start with a comment — must still be detected."""
    proxy, _, backup = _new_proxy_with_fake_db()
    sql = "-- migration v3\nALTER TABLE policies ADD COLUMN foo TEXT"
    op = proxy.executescript(sql)
    _run(op._await_operation())
    backup.backup_before_write.assert_called_once()


def test_pragma_does_not_trigger_backup() -> None:
    proxy, _, backup = _new_proxy_with_fake_db()
    op = proxy.execute("PRAGMA foreign_keys = ON")
    _run(op._await_operation())
    backup.backup_before_write.assert_not_called()


def test_executemany_write_triggers_backup_once() -> None:
    proxy, _, backup = _new_proxy_with_fake_db()
    op = proxy.executemany("INSERT INTO foo VALUES (?)", [(1,), (2,)])
    _run(op._await_operation())
    backup.backup_before_write.assert_called_once()


def test_async_context_manager_path_also_runs_backup() -> None:
    """``async with conn.execute(...)`` is the form used by every cursor read."""
    conn = importlib.import_module("database.connection")
    proxy, _, backup = _new_proxy_with_fake_db()

    fake_cursor = object()

    class _FakeOp:
        async def __aenter__(self):
            return fake_cursor

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def go():
        wrapper = conn.BackupAioSqliteOperation(
            proxy._backup_before_write_once("INSERT INTO foo VALUES (1)"),
            _FakeOp(),
        )
        async with wrapper as cursor:
            assert cursor is fake_cursor

    _run(go())
    backup.backup_before_write.assert_called_once()
