"""
Shared SQL SELECT fragments and row→schema mappers.

These were private helpers at the top of ``server.py`` (``_CUSTOMER_SELECT``,
``_POLICY_SELECT``, ``_policy_row_to_model``, ``_customer_row_to_model``). Now that
routes are split across modules, they live here so each router can reuse them
without duplication.
"""

from __future__ import annotations

from typing import Any, Optional

import aiosqlite
from fastapi import HTTPException

from schemas import Customer, Policy


# ---- SELECT fragments --------------------------------------------------------

CUSTOMER_SELECT = """
    SELECT
        c.customer_id AS id,
        c.user_id,
        c.full_name AS name,
        c.email,
        c.phone_number AS phone,
        (SELECT raw_address FROM customer_addresses a
         WHERE a.customer_id = c.customer_id ORDER BY a.address_id LIMIT 1) AS address,
        c.created_at
    FROM customers c
"""


POLICY_SELECT = """
    SELECT
        p.policy_id AS id,
        cu.user_id,
        p.customer_id,
        p.policy_no AS policy_number,
        it.insurance_type_name AS policy_type,
        co.company_name AS insurer_company,
        ps.status_name AS payment_status,
        p.payment_note AS payment_note,
        p.payment_updated_at AS payment_updated_at,
        p.date_of_issue AS start_date,
        p.policy_end_date AS end_date,
        p.total_premium AS premium,
        p.status,
        p.created_at,
        p.last_contacted_at AS last_contacted_at,
        p.contact_status AS contact_status,
        p.follow_up_date AS follow_up_date,
        p.renewal_status AS renewal_status,
        p.renewal_resolution_note AS renewal_resolution_note,
        p.renewal_resolved_at AS renewal_resolved_at,
        p.renewal_resolved_by AS renewal_resolved_by
    FROM policies p
    JOIN customers cu ON p.customer_id = cu.customer_id
    JOIN insurance_types it ON p.insurance_type_id = it.insurance_type_id
    LEFT JOIN companies co ON p.company_id = co.company_id
    LEFT JOIN payment_statuses ps ON p.payment_status_id = ps.payment_status_id
"""


# Wide join used by CSV / ZIP exports (includes LOB-specific detail columns).
EXPORT_POLICY_SELECT = """
    SELECT
        p.policy_id AS policy_id,
        p.source_record_id AS source_record_id,
        c.full_name AS customer_name,
        c.email AS customer_email,
        c.phone_number AS customer_phone,
        (SELECT raw_address FROM customer_addresses a
         WHERE a.customer_id = c.customer_id ORDER BY a.address_id LIMIT 1) AS customer_address,
        p.policy_no AS policy_number,
        it.insurance_type_name AS policy_type,
        it.category_group AS coverage_category,
        co.company_name AS insurer_company,
        p.ncb_discount AS ncb_discount,
        ps.status_name AS payment_status_name,
        ag.agent_name AS agent_name,
        p.card_details AS card_details,
        p.date_of_issue AS start_date,
        p.policy_end_date AS end_date,
        p.created_at AS created_at,
        p.updated_at AS updated_at,
        p.total_premium AS premium,
        p.status AS status,
        p.address_id AS policy_address_id,
        p.payment_note AS payment_note,
        p.payment_updated_at AS payment_updated_at,
        p.last_contacted_at AS last_contacted_at,
        p.contact_status AS contact_status,
        p.follow_up_date AS follow_up_date,
        p.renewal_status AS renewal_status,
        p.renewal_resolution_note AS renewal_resolution_note,
        p.renewal_resolved_at AS renewal_resolved_at,
        p.renewal_resolved_by AS renewal_resolved_by,
        m.vehicle_no AS motor_vehicle_no,
        m.vehicle_details AS motor_vehicle_details,
        m.idv_of_vehicle AS motor_idv,
        m.engine_no AS motor_engine_no,
        m.chassis_no AS motor_chassis_no,
        m.od_premium AS motor_od_premium,
        m.tp_premium AS motor_tp_premium,
        h.plan_name AS health_plan_name,
        h.sum_insured AS health_sum_insured,
        h.cover_type AS health_cover_type,
        h.members_covered AS health_members_covered,
        h.base_premium AS health_base_premium,
        h.additional_premium AS health_additional_premium,
        pr.product_name AS property_product_name,
        pr.sum_insured AS property_sum_insured,
        pr.sub_product AS property_sub_product,
        pr.risk_location AS property_risk_location,
        pr.base_premium AS property_base_premium,
        pr.additional_premium AS property_additional_premium
    FROM policies p
    JOIN customers c ON p.customer_id = c.customer_id
    JOIN insurance_types it ON p.insurance_type_id = it.insurance_type_id
    LEFT JOIN companies co ON p.company_id = co.company_id
    LEFT JOIN payment_statuses ps ON p.payment_status_id = ps.payment_status_id
    LEFT JOIN agents ag ON p.agent_id = ag.agent_id
    LEFT JOIN motor_policy_details m ON m.policy_id = p.policy_id
    LEFT JOIN health_policy_details h ON h.policy_id = p.policy_id
    LEFT JOIN property_policy_details pr ON pr.policy_id = p.policy_id
"""


# ---- ID parsing --------------------------------------------------------------

def parse_customer_id(customer_id: str) -> int:
    """Raise a 404 if the path segment isn't a positive integer — matches legacy behavior."""
    try:
        return int(customer_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Customer not found")


def parse_policy_id(policy_id: str) -> int:
    """Raise a 404 if the path segment isn't a positive integer — matches legacy behavior."""
    try:
        return int(policy_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Policy not found")


# ---- Row → schema mappers ----------------------------------------------------

def sql_float(v: Any) -> Optional[float]:
    """Best-effort numeric cast for SQLite NUMERIC columns that may contain text."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def customer_row_to_model(row: dict) -> Customer:
    """Materialize a ``_CUSTOMER_SELECT`` row into a :class:`Customer`."""
    return Customer(
        id=str(row["id"]),
        user_id=row["user_id"],
        name=row["name"] or "",
        email=row.get("email"),
        phone=row.get("phone"),
        address=row.get("address"),
        created_at=row["created_at"] or "",
    )


def policy_row_to_model(row: dict) -> Policy:
    """Materialize a ``_POLICY_SELECT`` row into a :class:`Policy`."""
    prem = row.get("premium")
    if prem is None:
        prem = 0.0
    else:
        try:
            prem = float(prem)
        except (TypeError, ValueError):
            prem = 0.0
    return Policy(
        id=str(row["id"]),
        user_id=row["user_id"],
        customer_id=str(row["customer_id"]),
        policy_number=row["policy_number"] or "",
        policy_type=row["policy_type"] or "",
        insurer_company=row.get("insurer_company"),
        payment_status=row.get("payment_status"),
        payment_note=row.get("payment_note"),
        payment_updated_at=row.get("payment_updated_at"),
        start_date=row["start_date"] or "",
        end_date=row["end_date"] or "",
        premium=prem,
        status=row["status"] or "active",
        created_at=row["created_at"] or "",
        last_contacted_at=row.get("last_contacted_at"),
        contact_status=(row.get("contact_status") or "Not Contacted").strip()
        or "Not Contacted",
        follow_up_date=row.get("follow_up_date"),
        renewal_status=(row.get("renewal_status") or "Open").strip() or "Open",
        renewal_resolution_note=row.get("renewal_resolution_note"),
        renewal_resolved_at=row.get("renewal_resolved_at"),
        renewal_resolved_by=row.get("renewal_resolved_by"),
    )


# ---- Reference-data helpers (used by create/update policy) ------------------

async def resolve_insurance_type_id(
    db: aiosqlite.Connection, slug_or_name: str
) -> int:
    """
    Map a manual-form slug (e.g. ``auto``) to an ``insurance_types.insurance_type_id``.
    Falls back to the first Motor type if the configured name isn't present — matches
    the old ``_resolve_insurance_type_id`` behavior.
    """
    from domain.constants import POLICY_SLUG_TO_TYPE_NAME

    name = POLICY_SLUG_TO_TYPE_NAME.get((slug_or_name or "auto").lower(), "Private Car")
    async with db.execute(
        "SELECT insurance_type_id FROM insurance_types WHERE insurance_type_name = ?",
        (name,),
    ) as cur:
        row = await cur.fetchone()
    if row:
        return int(row[0])
    async with db.execute(
        """SELECT insurance_type_id FROM insurance_types
           WHERE category_group = 'Motor' ORDER BY insurance_type_id LIMIT 1"""
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="insurance_types table is empty")
    return int(row[0])


async def default_payment_status_id(db: aiosqlite.Connection) -> Optional[int]:
    """Return the ``Unknown`` payment_status id, if seeded."""
    async with db.execute(
        "SELECT payment_status_id FROM payment_statuses WHERE status_name = 'Unknown' LIMIT 1"
    ) as cur:
        row = await cur.fetchone()
    return int(row[0]) if row else None


async def insert_empty_policy_detail(
    db: aiosqlite.Connection, policy_id: int, insurance_type_id: int
) -> None:
    """Insert a stub row into motor/health/property detail table based on category_group."""
    async with db.execute(
        "SELECT category_group FROM insurance_types WHERE insurance_type_id = ?",
        (insurance_type_id,),
    ) as cur:
        row = await cur.fetchone()
    cat = (row[0] if row else "Motor") or "Motor"
    if cat == "Motor":
        await db.execute(
            "INSERT INTO motor_policy_details (policy_id) VALUES (?)", (policy_id,)
        )
    elif cat == "Health":
        await db.execute(
            "INSERT INTO health_policy_details (policy_id) VALUES (?)", (policy_id,)
        )
    else:
        await db.execute(
            "INSERT INTO property_policy_details (policy_id) VALUES (?)", (policy_id,)
        )


async def payment_status_id_by_name(
    db: aiosqlite.Connection, name: str
) -> Optional[int]:
    async with db.execute(
        "SELECT payment_status_id FROM payment_statuses WHERE status_name = ?",
        (name,),
    ) as c:
        row = await c.fetchone()
    return int(row[0]) if row else None
