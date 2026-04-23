"""Renewal reminder buckets + expiring-policy list endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from typing import List

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query

from deps import get_current_user, get_db
from domain.dates import parse_policy_end_date_strict
from schemas import User

router = APIRouter(tags=["renewals"])


def _expiring_list_window_bounds(window: str, today: date) -> tuple[date, date]:
    """
    Inclusive ``[min_end, max_end]`` for policy_end_date, matching dashboard summary counts:

    - ``today``: end == today
    - ``7`` / ``15`` / ``30``: ``today <= end <= today + N``
      (same as ``expiring_within_*_days`` in /renewals/reminders).
    """
    if window == "today":
        return today, today
    if window == "7":
        return today, today + timedelta(days=7)
    if window == "15":
        return today, today + timedelta(days=15)
    if window == "30":
        return today, today + timedelta(days=30)
    raise ValueError(f"invalid window: {window}")


@router.get("/renewals/reminders")
async def get_renewal_reminders(
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Renewal buckets for active policies. Uses the server's **local calendar date** for
    ``today`` (policy end dates are calendar dates from imports).

    Summary (cumulative — active policies with end_date within next N days):
    - ``expiring_within_7_days``, ``expiring_within_15_days``, ``expiring_within_30_days``
      for the renewal reminders list.
    - ``expiring_within_365_days`` for the dashboard "Expiring soon (≤12 months)" metric card.
    """
    today = date.today()
    day_1 = today + timedelta(days=1)
    day_7 = today + timedelta(days=7)
    day_15 = today + timedelta(days=15)
    day_30 = today + timedelta(days=30)
    day_90 = today + timedelta(days=90)
    day_365 = today + timedelta(days=365)

    async with db.execute(
        """SELECT p.policy_id AS id, p.policy_no AS policy_number,
                  p.policy_end_date AS end_date, p.date_of_issue AS start_date,
                  p.total_premium AS premium, p.status,
                  it.insurance_type_name AS policy_type,
                  c.full_name AS customer_name, c.email AS customer_email
           FROM policies p
           JOIN customers c ON p.customer_id = c.customer_id
           JOIN insurance_types it ON p.insurance_type_id = it.insurance_type_id
           WHERE c.user_id = ? AND p.status = 'active'
           ORDER BY p.policy_end_date ASC""",
        (user.user_id,),
    ) as cursor:
        rows = await cursor.fetchall()

    reminders = {
        "today": [],
        "day_1": [],
        "day_7": [],
        "day_15": [],
        "day_30": [],
        "day_31_to_90": [],
        "day_91_to_365": [],
        "summary": {
            "expiring_today": 0,
            "expiring_within_7_days": 0,
            "expiring_within_15_days": 0,
            "expiring_within_30_days": 0,
            "expiring_within_365_days": 0,
            "expired": 0,
        },
    }

    for row in rows:
        policy_dict = dict(row)
        end_date = parse_policy_end_date_strict(policy_dict["end_date"])

        if end_date < today:
            reminders["summary"]["expired"] += 1
            continue

        if end_date == today:
            reminders["summary"]["expiring_today"] += 1

        if end_date <= day_365:
            reminders["summary"]["expiring_within_365_days"] += 1
        if end_date <= day_30:
            reminders["summary"]["expiring_within_30_days"] += 1
        if end_date <= day_15:
            reminders["summary"]["expiring_within_15_days"] += 1
        if end_date <= day_7:
            reminders["summary"]["expiring_within_7_days"] += 1

        if end_date > day_365:
            continue

        if end_date == today:
            reminders["today"].append(policy_dict)
        elif end_date == day_1:
            reminders["day_1"].append(policy_dict)
        elif day_1 < end_date <= day_7:
            reminders["day_7"].append(policy_dict)
        elif day_7 < end_date <= day_15:
            reminders["day_15"].append(policy_dict)
        elif day_15 < end_date <= day_30:
            reminders["day_30"].append(policy_dict)
        elif day_30 < end_date <= day_90:
            reminders["day_31_to_90"].append(policy_dict)
        elif day_90 < end_date <= day_365:
            reminders["day_91_to_365"].append(policy_dict)

    return reminders


@router.get("/renewals/expiring-list")
async def get_expiring_policies_list(
    window: str = Query(
        ...,
        description="today | 7 | 15 | 30 | expired — same rules as dashboard renewal summary",
        pattern="^(today|7|15|30|expired)$",
    ),
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Active policies whose end date falls in the same window as the dashboard renewal row counts.
    For ``expired``: active policies with policy_end_date before today (matches summary ``expired``).
    Non-expired windows: sorted by policy_end_date ascending. Expired: descending (most recent first).
    """
    today = date.today()

    if window == "expired":
        sql = """SELECT p.policy_id AS id, p.policy_no AS policy_number,
                       p.policy_end_date AS end_date,
                       p.total_premium AS premium,
                       it.insurance_type_name AS policy_type,
                       c.full_name AS customer_name,
                       c.phone_number AS customer_phone
                FROM policies p
                JOIN customers c ON p.customer_id = c.customer_id
                JOIN insurance_types it ON p.insurance_type_id = it.insurance_type_id
                WHERE c.user_id = ? AND p.status = 'active'
                  AND date(p.policy_end_date) < date(?)
                ORDER BY p.policy_end_date DESC, p.policy_id ASC"""
        params = (user.user_id, today.isoformat())
    else:
        try:
            d_min, d_max = _expiring_list_window_bounds(window, today)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid window")
        sql = """SELECT p.policy_id AS id, p.policy_no AS policy_number,
                       p.policy_end_date AS end_date,
                       p.total_premium AS premium,
                       it.insurance_type_name AS policy_type,
                       c.full_name AS customer_name,
                       c.phone_number AS customer_phone
                FROM policies p
                JOIN customers c ON p.customer_id = c.customer_id
                JOIN insurance_types it ON p.insurance_type_id = it.insurance_type_id
                WHERE c.user_id = ? AND p.status = 'active'
                  AND date(p.policy_end_date) >= date(?)
                  AND date(p.policy_end_date) <= date(?)
                ORDER BY p.policy_end_date ASC, p.policy_id ASC"""
        params = (user.user_id, d_min.isoformat(), d_max.isoformat())

    async with db.execute(sql, params) as cursor:
        rows = await cursor.fetchall()

    out: List[dict] = []
    for row in rows:
        d = dict(row)
        end_d = parse_policy_end_date_strict(d["end_date"])
        days_left = (end_d - today).days
        prem = d.get("premium")
        out.append(
            {
                "id": int(d["id"]),
                "policy_number": d.get("policy_number"),
                "end_date": d.get("end_date"),
                "premium": float(prem) if prem is not None else None,
                "policy_type": d.get("policy_type"),
                "customer_name": d.get("customer_name"),
                "customer_phone": d.get("customer_phone"),
                "days_left": int(days_left),
            }
        )
    return out
