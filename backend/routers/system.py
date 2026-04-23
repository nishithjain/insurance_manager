"""Root + health endpoints under ``/api/``."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter

from db_path import DB_PATH

router = APIRouter(tags=["system"])


@router.get("/")
async def root():
    return {"message": "Insurance App API", "version": "1.0.0"}


@router.get("/health")
async def health():
    """Liveness + SQLite row counts (verify the API uses the DB file you expect)."""
    out: dict = {
        "status": "healthy",
        "database_path": str(DB_PATH.resolve()),
        "database_exists": DB_PATH.is_file(),
    }
    if not out["database_exists"]:
        out["hint"] = (
            "No insurance.db yet. Run the API from backend/ (see run_backend.sh) so the file is "
            "created next to server.py, or set INSURANCE_DB_PATH in backend/.env to an absolute path."
        )
        return out
    try:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            for table in ("users", "customers", "policies", "statement_policy_lines"):
                try:
                    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    out[f"count_{table}"] = n
                except sqlite3.OperationalError:
                    out[f"count_{table}"] = None
        finally:
            conn.close()
    except OSError as e:
        out["database_error"] = str(e)
    return out
