"""Pydantic schemas for the single-tenant data-owner user."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    """Default data-owner row in ``users``. All customers/policies FK here."""

    user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    created_at: str
