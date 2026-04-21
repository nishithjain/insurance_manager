"""
SQLite file location for this app. No aiosqlite — import this from CLI tools without full venv deps.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass


def resolve_db_path() -> Path:
    override = (os.environ.get("INSURANCE_DB_PATH") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent / "insurance.db"


DB_PATH = resolve_db_path()
