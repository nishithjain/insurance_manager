"""
Aggregated insurance statistics for the dashboard (per-user, from SQLite).

Date rules:
- Current calendar month uses the server's local date via datetime.date.today().
- policy_end_date / renewal_resolved_at / payment timestamps compared as DATE where possible.

NOTE: Named insurance_statistics.py to avoid shadowing Python's stdlib `statistics` module.
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from database import get_db

PENDING_UPPER = "PENDING"


def _month_bounds(d: date) -> Tuple[date, date]:
    """First and last day of month containing d."""
    first = d.replace(day=1)
    last_day = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=last_day)
    return first, last


def _add_months(d: date, delta: int) -> date:
    m = d.month - 1 + delta
    y = d.year + m // 12
    m = m % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


async def get_pending_payments(db: aiosqlite.Connection, user_id: str) -> Dict[str, Any]:
    """Count and premium sum for policies whose payment status is PENDING."""
    q = """
        SELECT COUNT(*), COALESCE(SUM(p.total_premium), 0)
        FROM policies p
        JOIN customers c ON p.customer_id = c.customer_id
        LEFT JOIN payment_statuses ps ON p.payment_status_id = ps.payment_status_id
        WHERE c.user_id = ?
          AND UPPER(TRIM(COALESCE(ps.status_name, ''))) = ?
    """
    async with db.execute(q, (user_id, PENDING_UPPER)) as cur:
        row = await cur.fetchone()
    return {"count": int(row[0]), "amount": float(row[1] or 0)}


async def get_monthly_payments_received(
    db: aiosqlite.Connection, user_id: str, month_start: date, month_end: date
) -> float:
    """
    Sum of premiums for non-PENDING payment status where the activity date falls in [month_start, month_end].
    Uses COALESCE(payment_updated_at, updated_at) as the activity date.
    """
    q = """
        SELECT COALESCE(SUM(p.total_premium), 0)
        FROM policies p
        JOIN customers c ON p.customer_id = c.customer_id
        LEFT JOIN payment_statuses ps ON p.payment_status_id = ps.payment_status_id
        WHERE c.user_id = ?
          AND ps.status_name IS NOT NULL
          AND UPPER(TRIM(ps.status_name)) != ?
          AND date(COALESCE(p.payment_updated_at, p.updated_at)) >= date(?)
          AND date(COALESCE(p.payment_updated_at, p.updated_at)) <= date(?)
    """
    async with db.execute(
        q,
        (user_id, PENDING_UPPER, month_start.isoformat(), month_end.isoformat()),
    ) as cur:
        row = await cur.fetchone()
    return float(row[0] or 0)


async def get_renewal_stats(
    db: aiosqlite.Connection, user_id: str, month_start: date, month_end: date
) -> Dict[str, Any]:
    renewals_q = """
        SELECT COUNT(*)
        FROM policies p
        JOIN customers c ON p.customer_id = c.customer_id
        WHERE c.user_id = ?
          AND p.renewal_status IN ('RenewedWithUs', 'RenewedElsewhere')
          AND p.renewal_resolved_at IS NOT NULL
          AND date(p.renewal_resolved_at) >= date(?)
          AND date(p.renewal_resolved_at) <= date(?)
    """
    async with db.execute(
        renewals_q, (user_id, month_start.isoformat(), month_end.isoformat())
    ) as cur:
        renewals_this_month = int((await cur.fetchone())[0])

    expiring_q = """
        SELECT COUNT(*)
        FROM policies p
        JOIN customers c ON p.customer_id = c.customer_id
        WHERE c.user_id = ?
          AND p.status = 'active'
          AND p.policy_end_date IS NOT NULL
          AND date(p.policy_end_date) >= date(?)
          AND date(p.policy_end_date) <= date(?)
    """
    async with db.execute(
        expiring_q, (user_id, month_start.isoformat(), month_end.isoformat())
    ) as cur:
        expiring_this_month = int((await cur.fetchone())[0])

    rate: Optional[float]
    if expiring_this_month <= 0:
        rate = None
    else:
        rate = round(renewals_this_month / expiring_this_month, 4)

    return {
        "renewals_this_month": renewals_this_month,
        "expiring_this_month": expiring_this_month,
        "renewal_conversion_rate": rate,
    }


async def get_expired_not_renewed_open(db: aiosqlite.Connection, user_id: str) -> int:
    """Active policies past end date with renewal still Open (missed opportunities)."""
    q = """
        SELECT COUNT(*)
        FROM policies p
        JOIN customers c ON p.customer_id = c.customer_id
        WHERE c.user_id = ?
          AND p.status = 'active'
          AND p.policy_end_date IS NOT NULL
          AND date(p.policy_end_date) < date('now')
          AND p.renewal_status = 'Open'
    """
    async with db.execute(q, (user_id,)) as cur:
        return int((await cur.fetchone())[0])


async def get_customer_stats(db: aiosqlite.Connection, user_id: str) -> Dict[str, int]:
    total_q = "SELECT COUNT(*) FROM customers WHERE user_id = ?"
    async with db.execute(total_q, (user_id,)) as cur:
        total = int((await cur.fetchone())[0])

    repeat_q = """
        SELECT COUNT(*) FROM (
            SELECT c.customer_id
            FROM customers c
            JOIN policies p ON p.customer_id = c.customer_id
            WHERE c.user_id = ?
            GROUP BY c.customer_id
            HAVING COUNT(p.policy_id) > 1
        )
    """
    async with db.execute(repeat_q, (user_id,)) as cur:
        repeat_n = int((await cur.fetchone())[0])

    return {"total_customers": total, "repeat_customers": repeat_n}


async def get_monthly_trend(
    db: aiosqlite.Connection, user_id: str, months_back: int = 6
) -> List[Dict[str, Any]]:
    """
    Last `months_back` calendar months (including current partial month).
    Each row: month label (YYYY-MM), payments_received, renewals, expiring_count.
    """
    today = date.today()
    out: List[Dict[str, Any]] = []
    for i in range(months_back - 1, -1, -1):
        ref = _add_months(today.replace(day=1), -i)
        first, last = _month_bounds(ref)
        key = f"{ref.year:04d}-{ref.month:02d}"
        pay = await get_monthly_payments_received(db, user_id, first, last)
        rq = """
            SELECT COUNT(*) FROM policies p
            JOIN customers c ON p.customer_id = c.customer_id
            WHERE c.user_id = ?
              AND p.renewal_status IN ('RenewedWithUs', 'RenewedElsewhere')
              AND p.renewal_resolved_at IS NOT NULL
              AND date(p.renewal_resolved_at) >= date(?)
              AND date(p.renewal_resolved_at) <= date(?)
        """
        async with db.execute(rq, (user_id, first.isoformat(), last.isoformat())) as cur:
            renewals = int((await cur.fetchone())[0])
        eq = """
            SELECT COUNT(*) FROM policies p
            JOIN customers c ON p.customer_id = c.customer_id
            WHERE c.user_id = ?
              AND p.status = 'active'
              AND p.policy_end_date IS NOT NULL
              AND date(p.policy_end_date) >= date(?)
              AND date(p.policy_end_date) <= date(?)
        """
        async with db.execute(eq, (user_id, first.isoformat(), last.isoformat())) as cur:
            expiring = int((await cur.fetchone())[0])
        out.append(
            {
                "month": key,
                "payments_received": pay,
                "renewals": renewals,
                "expiring": expiring,
            }
        )
    return out


async def get_total_policies(db: aiosqlite.Connection, user_id: str) -> int:
    """All policies for the user (any status)."""
    q = """
        SELECT COUNT(*) FROM policies p
        JOIN customers c ON p.customer_id = c.customer_id
        WHERE c.user_id = ?
    """
    async with db.execute(q, (user_id,)) as cur:
        return int((await cur.fetchone())[0])


async def get_policy_type_distribution(
    db: aiosqlite.Connection, user_id: str
) -> List[Dict[str, Any]]:
    q = """
        SELECT it.insurance_type_name AS policy_type, COUNT(*) AS cnt
        FROM policies p
        JOIN customers c ON p.customer_id = c.customer_id
        JOIN insurance_types it ON p.insurance_type_id = it.insurance_type_id
        WHERE c.user_id = ?
        GROUP BY it.insurance_type_name
        ORDER BY cnt DESC
    """
    async with db.execute(q, (user_id,)) as cur:
        rows = await cur.fetchall()
    return [{"policy_type": r[0] or "Unknown", "count": int(r[1])} for r in rows]


async def build_dashboard_statistics(user_id: str) -> Dict[str, Any]:
    """Compose all dashboard stats for one user."""
    today = date.today()
    month_start, month_end = _month_bounds(today)

    db = await get_db()
    try:
        pending = await get_pending_payments(db, user_id)
        received = await get_monthly_payments_received(db, user_id, month_start, month_end)
        renewal = await get_renewal_stats(db, user_id, month_start, month_end)
        expired_open = await get_expired_not_renewed_open(db, user_id)
        customers = await get_customer_stats(db, user_id)
        trend = await get_monthly_trend(db, user_id, 6)
        dist = await get_policy_type_distribution(db, user_id)
        total_policies = await get_total_policies(db, user_id)

        return {
            "payment_received_this_month": received,
            "pending_payments_count": pending["count"],
            "pending_payments_amount": pending["amount"],
            "renewals_this_month": renewal["renewals_this_month"],
            "expiring_this_month": renewal["expiring_this_month"],
            "renewal_conversion_rate": renewal["renewal_conversion_rate"],
            "expired_not_renewed_open": expired_open,
            "total_customers": customers["total_customers"],
            "total_policies": total_policies,
            "repeat_customers": customers["repeat_customers"],
            "monthly_trend": trend,
            "policy_type_distribution": dist,
            "as_of_date": today.isoformat(),
            "current_month_label": f"{today.year:04d}-{today.month:02d}",
        }
    finally:
        await db.close()
