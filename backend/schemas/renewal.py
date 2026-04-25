"""Pydantic schemas for renewal-history records."""

from __future__ import annotations

from pydantic import BaseModel


class RenewalHistory(BaseModel):
    id: str
    policy_id: str
    renewal_date: str
    amount: float
    status: str
    created_at: str


class RenewalHistoryCreate(BaseModel):
    policy_id: str
    renewal_date: str
    amount: float
    status: str = "completed"
