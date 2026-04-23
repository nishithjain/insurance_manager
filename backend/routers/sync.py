"""Offline snapshot / sync-status / dashboard statistics endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends

from deps import get_current_user, get_db
from insurance_statistics import build_dashboard_statistics
from repositories.sql import (
    CUSTOMER_SELECT,
    POLICY_SELECT,
    customer_row_to_model,
    policy_row_to_model,
)
from schemas import User

router = APIRouter(tags=["sync"])


async def _load_user_snapshot_payload(
    db: aiosqlite.Connection, user_id: str
) -> dict:
    snapshot = {
        "version": datetime.now(timezone.utc).isoformat(),
        "schema": "normalized_v2",
        "user_id": user_id,
        "customers": [],
        "policies": [],
        "renewal_history": [],
    }
    async with db.execute(
        f"{CUSTOMER_SELECT} WHERE c.user_id = ?",
        (user_id,),
    ) as cursor:
        for row in await cursor.fetchall():
            snapshot["customers"].append(
                customer_row_to_model(dict(row)).model_dump()
            )
    async with db.execute(
        f"{POLICY_SELECT} WHERE cu.user_id = ?",
        (user_id,),
    ) as cursor:
        for row in await cursor.fetchall():
            snapshot["policies"].append(
                policy_row_to_model(dict(row)).model_dump()
            )
    async with db.execute(
        """SELECT rh.* FROM renewal_history rh
           JOIN policies p ON rh.policy_id = p.policy_id
           JOIN customers c ON p.customer_id = c.customer_id
           WHERE c.user_id = ?""",
        (user_id,),
    ) as cursor:
        snapshot["renewal_history"] = [dict(row) for row in await cursor.fetchall()]
    return snapshot


@router.post("/sync/generate-snapshot")
async def generate_snapshot(
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Build JSON snapshot (Customer, Policy, RenewalHistory) for offline/import."""
    return await _load_user_snapshot_payload(db, user.user_id)


@router.get("/sync/status")
async def get_sync_status(
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Latest sync_info row for the user."""
    async with db.execute(
        "SELECT * FROM sync_info WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user.user_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return {"last_sync": None, "status": "never_synced"}
    return dict(row)


@router.get("/statistics/dashboard")
async def statistics_dashboard(
    user: User = Depends(get_current_user),
):
    """Payment, renewal, expiry, and customer metrics (current month + trends)."""
    return await build_dashboard_statistics(user.user_id)
