"""SQLite backup support driven by the app_settings table."""

from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
import threading
from datetime import date
from pathlib import Path
from typing import Optional

from db_path import DB_PATH

logger = logging.getLogger(__name__)

BACKUP_FOLDER_SETTING_KEY = "database_backup_folder"
PRE_MODIFY_BACKUP_FILENAME = "insurance_pre_modify_backup.db"
DAILY_BACKUP_FILENAME = "insurance_daily_backup.db"

_BACKUP_LOCK = threading.Lock()


class DatabaseBackupService:
    """Create SQLite-safe backups without making business writes depend on them."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    def backup_before_write(self) -> None:
        """Best-effort pre-write backup plus once-per-day backup."""
        backup_dir = self._configured_backup_dir()
        if backup_dir is None:
            return

        with _BACKUP_LOCK:
            try:
                backup_dir.mkdir(parents=True, exist_ok=True)
                if not backup_dir.is_dir():
                    logger.error("Database backup path is not a directory: %s", backup_dir)
                    return

                self._backup_to(backup_dir / PRE_MODIFY_BACKUP_FILENAME)
                daily_path = backup_dir / DAILY_BACKUP_FILENAME
                if self._daily_backup_due(daily_path):
                    self._backup_to(daily_path)
            except Exception:
                logger.exception("Database backup failed for configured path: %s", backup_dir)

    def _configured_backup_dir(self) -> Optional[Path]:
        raw = self._read_backup_folder_setting()
        if raw is None or not raw.strip():
            return None
        try:
            return Path(raw.strip()).expanduser().resolve()
        except Exception:
            logger.exception("Invalid database backup folder setting: %r", raw)
            return None

    def _read_backup_folder_setting(self) -> Optional[str]:
        if not self.db_path.is_file():
            return None
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                row = conn.execute(
                    "SELECT value FROM app_settings WHERE key = ?",
                    (BACKUP_FOLDER_SETTING_KEY,),
                ).fetchone()
                return str(row[0]) if row and row[0] is not None else None
            finally:
                conn.close()
        except sqlite3.OperationalError:
            return None
        except Exception:
            logger.exception("Could not read database backup folder setting")
            return None

    def _backup_to(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=str(destination.parent),
        )
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            source_uri = f"file:{self.db_path.as_posix()}?mode=ro"
            source = sqlite3.connect(source_uri, uri=True)
            try:
                target = sqlite3.connect(str(tmp_path))
                try:
                    source.backup(target)
                    target.commit()
                finally:
                    target.close()
            finally:
                source.close()
            os.replace(tmp_path, destination)
            logger.info("Database backup written: %s", destination)
        except Exception:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove failed backup temp file: %s", tmp_path)
            raise

    def _daily_backup_due(self, path: Path) -> bool:
        if not path.exists():
            return True
        try:
            return date.fromtimestamp(path.stat().st_mtime) != date.today()
        except OSError:
            return True


def backup_database_before_write() -> None:
    """Convenience entry point for direct sqlite3 scripts."""
    DatabaseBackupService().backup_before_write()
