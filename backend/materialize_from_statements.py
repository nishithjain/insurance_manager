"""
Create customers + policies from statement_policy_lines for a given user_id (same as dashboard button).

CSV import only fills statement_policy_lines. This step is required for the customers/policies tables.

Usage (from backend/, venv active, PYTHONHOME unset):
  python materialize_from_statements.py
  python materialize_from_statements.py --user-id user_abc123

List user ids in the database:
  python materialize_from_statements.py --list-users
"""
from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys

from db_path import DB_PATH


def _list_users() -> None:
    conn = sqlite3.connect(str(DB_PATH))
    try:
        rows = conn.execute("SELECT user_id, email, name FROM users ORDER BY created_at").fetchall()
        if not rows:
            print("No users in database — sign in once via the app or dev login first.")
            return
        for uid, email, name in rows:
            print(f"  {uid}\t{email}\t{name or ''}")
    finally:
        conn.close()


async def _run(user_id: str) -> int:
    from database import get_db
    from statement_materialize import materialize_statement_lines

    db = await get_db()
    try:
        stats = await materialize_statement_lines(db, user_id)
        await db.commit()
        print(stats)
        return 0
    finally:
        await db.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Materialize statement CSV rows into customers/policies")
    p.add_argument(
        "--user-id",
        default="user_dev_local",
        help="users.user_id that should own the imported rows (default: dev user)",
    )
    p.add_argument("--list-users", action="store_true", help="Print user_id values and exit")
    args = p.parse_args()
    if args.list_users:
        _list_users()
        sys.exit(0)
    if not DB_PATH.is_file():
        print(f"No database at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        ok = conn.execute(
            "SELECT 1 FROM users WHERE user_id = ? LIMIT 1", (args.user_id,)
        ).fetchone()
    finally:
        conn.close()
    if not ok:
        print(
            f"No user {args.user_id!r} in the database. Sign in once in the app, or run:\n"
            f"  python materialize_from_statements.py --list-users",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        sys.exit(asyncio.run(_run(args.user_id)))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
