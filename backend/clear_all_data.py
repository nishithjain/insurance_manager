"""
Delete all rows from application tables in insurance.db (keeps schema).
Run from backend/: python clear_all_data.py

Use --db to target an installed database:
python clear_all_data.py --db "C:\\Program Files\\InsuranceManagerBackend\\backend\\insurance.db"

Order is safe with foreign_keys=OFF (default for this script).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from db_path import DB_PATH
from services.database_backup import DatabaseBackupService

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clear all application data from an Insurance Manager SQLite database."
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        help=(
            "SQLite database path to clear. Defaults to INSURANCE_DB_PATH, "
            "then backend/insurance.db."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db_path).expanduser().resolve() if args.db_path else DB_PATH

    if not db_path.is_file():
        print(f"No database at {db_path}", file=sys.stderr)
        sys.exit(1)
    DatabaseBackupService(db_path).backup_before_write()
    conn = sqlite3.connect(str(db_path))
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
    print(f"Cleared data from {db_path}")


if __name__ == "__main__":
    main()
