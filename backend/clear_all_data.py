"""
Delete all rows from application tables in insurance.db (keeps schema).
Run from backend/: python clear_all_data.py

Order is safe with foreign_keys=OFF (default for this script).
"""
from __future__ import annotations

import sqlite3
import sys

from db_path import DB_PATH
from services.database_backup import backup_database_before_write

TABLES = [
    "motor_policy_details",
    "health_policy_details",
    "property_policy_details",
    "renewal_history",
    "policies",
    "customer_addresses",
    "customers",
    "statement_policy_lines",
    "user_sessions",
    "sync_info",
    "drive_credentials",
    "users",
]


def main() -> None:
    if not DB_PATH.is_file():
        print(f"No database at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    backup_database_before_write()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        for t in TABLES:
            try:
                conn.execute(f"DELETE FROM {t}")
            except sqlite3.OperationalError as e:
                print(f"Skip {t}: {e}", file=sys.stderr)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("DELETE FROM sqlite_sequence")
        except sqlite3.OperationalError:
            pass
        conn.commit()
    finally:
        conn.close()
    print(f"Cleared data from {DB_PATH}")


if __name__ == "__main__":
    main()
