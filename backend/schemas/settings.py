"""Pydantic schemas for app-level settings (currently just backup folder)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AppSettings(BaseModel):
    database_backup_folder: Optional[str] = None


class AppSettingsUpdate(BaseModel):
    database_backup_folder: Optional[str] = None
