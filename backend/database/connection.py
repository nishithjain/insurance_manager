"""
Connection lifecycle and the backup-on-first-write proxy.

This module owns the *only* path through which the rest of the backend
acquires an ``aiosqlite`` connection: ``get_db`` returns a thin
:class:`BackupAioSqliteConnection` proxy that triggers the configured
:class:`DatabaseBackupService` exactly once before the first write of
that connection, no matter which router/repository issued it.

``init_db`` runs schema creation, all idempotent migrations, and reference
seeding. Called from ``server.py`` at startup and from
``recreate_database.py`` for rebuilds.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import aiosqlite

from db_path import DB_PATH
from services.database_backup import DatabaseBackupService

from .migrations import apply_migrations
from .schema import SCHEMA_SQL
from .seed import seed_reference_data

logger = logging.getLogger(__name__)


# Matches the first SQL statement to decide whether the about-to-run query
# mutates the database. Comments at the top are skipped so prepared
# scripts that begin with ``-- ...`` still classify correctly.
_WRITE_SQL_RE = re.compile(
    r"^\s*(?:--[^\n]*\n\s*)*(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|VACUUM)\b",
    re.IGNORECASE,
)


class BackupAioSqliteConnection:
    """Thin proxy that runs one configured DB backup before the first write."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db
        self._backup_service = DatabaseBackupService()
        self._backup_checked = False

    def __getattr__(self, name: str):
        return getattr(self._db, name)

    def _is_write_sql(self, sql: str) -> bool:
        return bool(_WRITE_SQL_RE.match(sql or ""))

    async def _backup_before_write_once(self, sql: str) -> None:
        if self._backup_checked or not self._is_write_sql(sql):
            return
        self._backup_service.backup_before_write()
        self._backup_checked = True

    def execute(self, sql: str, parameters: Any = None):
        if parameters is None:
            operation = self._db.execute(sql)
        else:
            operation = self._db.execute(sql, parameters)
        return BackupAioSqliteOperation(
            self._backup_before_write_once(sql),
            operation,
        )

    def executemany(self, sql: str, parameters):
        return BackupAioSqliteOperation(
            self._backup_before_write_once(sql),
            self._db.executemany(sql, parameters),
        )

    def executescript(self, sql_script: str):
        return BackupAioSqliteOperation(
            self._backup_before_write_once(sql_script),
            self._db.executescript(sql_script),
        )


class BackupAioSqliteOperation:
    """Preserve aiosqlite's awaitable + async-context-manager behaviour."""

    def __init__(self, backup_coro, operation) -> None:
        self._backup_coro = backup_coro
        self._operation = operation
        self._backup_done = False

    async def _run_backup_once(self) -> None:
        if self._backup_done:
            return
        await self._backup_coro
        self._backup_done = True

    async def _await_operation(self):
        await self._run_backup_once()
        return await self._operation

    def __await__(self):
        return self._await_operation().__await__()

    async def __aenter__(self):
        await self._run_backup_once()
        return await self._operation.__aenter__()

    async def __aexit__(self, exc_type, exc, tb):
        return await self._operation.__aexit__(exc_type, exc, tb)


async def init_db() -> None:
    """Create schema, run migrations, and seed reference data."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        DatabaseBackupService().backup_before_write()
        await db.executescript(SCHEMA_SQL)
        await apply_migrations(db)
        await seed_reference_data(db)
        await db.commit()
        logger.info("Database initialized successfully")


async def get_db() -> BackupAioSqliteConnection:
    """Open an aiosqlite connection wrapped with the backup-on-first-write proxy."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return BackupAioSqliteConnection(db)


__all__ = [
    "BackupAioSqliteConnection",
    "BackupAioSqliteOperation",
    "init_db",
    "get_db",
]
