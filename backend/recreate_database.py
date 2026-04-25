"""
Delete insurance.db and create a fresh file with the current schema + seed data.

Run from backend/:
  python recreate_database.py

Requires INSURANCE_DB_PATH or default path next to db_path.py. All data is lost.
"""
from __future__ import annotations

import asyncio
import os
import sys

from db_path import DB_PATH
from database import init_db
from services.database_backup import backup_database_before_write


def main() -> None:
    if DB_PATH.is_file():
        backup_database_before_write()
        try:
            os.unlink(DB_PATH)
        except OSError as e:
            print(f"Could not remove {DB_PATH}: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Removed {DB_PATH.resolve()}")
    asyncio.run(init_db())
    print(f"Created fresh database at {DB_PATH.resolve()}")


if __name__ == "__main__":
    main()
