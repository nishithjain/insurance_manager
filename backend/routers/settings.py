"""Application settings endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends

from deps import get_db
from schemas import AppSettings, AppSettingsUpdate
from services.database_backup import BACKUP_FOLDER_SETTING_KEY

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=AppSettings)
async def get_settings(
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (BACKUP_FOLDER_SETTING_KEY,),
    ) as cur:
        row = await cur.fetchone()
    return AppSettings(database_backup_folder=row[0] if row else None)


@router.put("/settings", response_model=AppSettings)
async def update_settings(
    body: AppSettingsUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    value = (body.database_backup_folder or "").strip()
    now = datetime.now(timezone.utc).isoformat()
    if value:
        await db.execute(
            """INSERT INTO app_settings (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (BACKUP_FOLDER_SETTING_KEY, value, now),
        )
    else:
        await db.execute(
            "DELETE FROM app_settings WHERE key = ?",
            (BACKUP_FOLDER_SETTING_KEY,),
        )
    await db.commit()
    return AppSettings(database_backup_folder=value or None)
