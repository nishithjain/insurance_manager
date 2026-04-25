"""
Database package: schema, migrations, seeds, and the connection lifecycle.

This module preserves backward compatibility with the historical
``backend/database.py`` flat module by re-exporting the same public
names (``init_db``, ``get_db``, ``BackupAioSqliteConnection``,
``BackupAioSqliteOperation``, ``SCHEMA_SQL``,
``export_user_insurance_sqlite_bytes``). Existing imports such as
``from database import init_db`` keep working unchanged.

New code should prefer the explicit submodules:

  * ``database.connection`` — connection lifecycle + backup proxy
  * ``database.schema``     — canonical CREATE TABLE script
  * ``database.migrations`` — idempotent ALTER/UPDATE migrations
  * ``database.seed``       — reference data + bootstrap admin
  * ``database.user_export``— per-user SQLite snapshot helper
"""

from .connection import (
    BackupAioSqliteConnection,
    BackupAioSqliteOperation,
    get_db,
    init_db,
)
from .schema import SCHEMA_SQL
from .user_export import export_user_insurance_sqlite_bytes

__all__ = [
    "BackupAioSqliteConnection",
    "BackupAioSqliteOperation",
    "init_db",
    "get_db",
    "SCHEMA_SQL",
    "export_user_insurance_sqlite_bytes",
]
