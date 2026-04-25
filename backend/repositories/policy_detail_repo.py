"""
Reads against the per-line-of-business detail tables
(``motor_policy_details`` / ``health_policy_details`` / ``property_policy_details``)
and the legacy ``insurance_types.category_group`` lookup that drives the
mobile read-only detail bundle.
"""

from __future__ import annotations

from typing import Optional

import aiosqlite

from schemas import (
    HealthPolicyDetailsDto,
    MotorPolicyDetailsDto,
    PropertyPolicyDetailsDto,
)

from ._helpers import sql_float


async def get_category_group(db: aiosqlite.Connection, policy_id: int) -> str:
    """
    Return the legacy ``insurance_types.category_group`` for a policy, or
    ``"Motor"`` as the historical fallback when nothing is found. The
    fallback matches the prior ``router/policies.py`` behavior so callers
    don't need to special-case missing rows.
    """
    async with db.execute(
        """SELECT it.category_group FROM policies p
           JOIN insurance_types it ON p.insurance_type_id = it.insurance_type_id
           WHERE p.policy_id = ?""",
        (policy_id,),
    ) as cur:
        row = await cur.fetchone()
    return (row[0] if row else "Motor") or "Motor"


async def load_motor_details(
    db: aiosqlite.Connection, policy_id: int
) -> Optional[MotorPolicyDetailsDto]:
    async with db.execute(
        """SELECT vehicle_no, vehicle_details, idv_of_vehicle, engine_no, chassis_no,
                  od_premium, tp_premium
           FROM motor_policy_details WHERE policy_id = ?""",
        (policy_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    md = dict(row)
    return MotorPolicyDetailsDto(
        vehicle_no=md.get("vehicle_no"),
        vehicle_details=md.get("vehicle_details"),
        idv_of_vehicle=sql_float(md.get("idv_of_vehicle")),
        engine_no=md.get("engine_no"),
        chassis_no=md.get("chassis_no"),
        od_premium=sql_float(md.get("od_premium")),
        tp_premium=sql_float(md.get("tp_premium")),
    )


async def load_health_details(
    db: aiosqlite.Connection, policy_id: int
) -> Optional[HealthPolicyDetailsDto]:
    async with db.execute(
        """SELECT plan_name, sum_insured, cover_type, members_covered,
                  base_premium, additional_premium
           FROM health_policy_details WHERE policy_id = ?""",
        (policy_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    hd = dict(row)
    return HealthPolicyDetailsDto(
        plan_name=hd.get("plan_name"),
        sum_insured=sql_float(hd.get("sum_insured")),
        cover_type=hd.get("cover_type"),
        members_covered=hd.get("members_covered"),
        base_premium=sql_float(hd.get("base_premium")),
        additional_premium=sql_float(hd.get("additional_premium")),
    )


async def load_property_details(
    db: aiosqlite.Connection, policy_id: int
) -> Optional[PropertyPolicyDetailsDto]:
    async with db.execute(
        """SELECT product_name, sum_insured, sub_product, risk_location,
                  base_premium, additional_premium
           FROM property_policy_details WHERE policy_id = ?""",
        (policy_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    pd = dict(row)
    return PropertyPolicyDetailsDto(
        product_name=pd.get("product_name"),
        sum_insured=sql_float(pd.get("sum_insured")),
        sub_product=pd.get("sub_product"),
        risk_location=pd.get("risk_location"),
        base_premium=sql_float(pd.get("base_premium")),
        additional_premium=sql_float(pd.get("additional_premium")),
    )
