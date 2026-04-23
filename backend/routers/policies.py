"""Policy CRUD + PATCH workflows + read-only detail bundle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from deps import get_current_user, get_db
from domain.constants import (
    ALLOWED_PAYMENT_UPDATE_FROM_PENDING,
    ALLOWED_POLICY_CONTACT_STATUSES,
    ALLOWED_RENEWAL_STATUSES,
    is_pending_payment_label,
)
from repositories.sql import (
    CUSTOMER_SELECT,
    POLICY_SELECT,
    customer_row_to_model,
    default_payment_status_id,
    insert_empty_policy_detail,
    parse_policy_id,
    payment_status_id_by_name,
    policy_row_to_model,
    resolve_insurance_type_id,
    sql_float,
)
from schemas import (
    HealthPolicyDetailsDto,
    MotorPolicyDetailsDto,
    Policy,
    PolicyContactUpdate,
    PolicyCreate,
    PolicyDetailBundle,
    PolicyPaymentUpdate,
    PolicyRenewalResolutionUpdate,
    PropertyPolicyDetailsDto,
    User,
)

router = APIRouter(tags=["policies"])


@router.get("/policies", response_model=List[Policy])
async def get_policies(
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all policies for current user."""
    async with db.execute(
        f"{POLICY_SELECT} WHERE cu.user_id = ? ORDER BY p.created_at DESC",
        (user.user_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [policy_row_to_model(dict(row)) for row in rows]


@router.post("/policies", response_model=Policy)
async def create_policy(
    policy: PolicyCreate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new policy."""
    try:
        cust_pk = int(policy.customer_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Customer not found")

    async with db.execute(
        "SELECT customer_id FROM customers WHERE customer_id = ? AND user_id = ?",
        (cust_pk, user.user_id),
    ) as cursor:
        customer = await cursor.fetchone()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    it_id = await resolve_insurance_type_id(db, policy.policy_type)
    pay_id = await default_payment_status_id(db)

    created_at = datetime.now(timezone.utc).isoformat()
    source_record_id = f"manual-{uuid.uuid4().hex}"

    await db.execute(
        """INSERT INTO policies (
            source_record_id, customer_id, address_id, insurance_type_id,
            company_id, agent_id, ncb_discount, total_premium, payment_status_id,
            date_of_issue, policy_end_date, policy_no, card_details, status,
            last_contacted_at, contact_status, follow_up_date,
            renewal_status, renewal_resolution_note, renewal_resolved_at, renewal_resolved_by,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            source_record_id,
            cust_pk,
            None,
            it_id,
            None,
            None,
            None,
            policy.premium,
            pay_id,
            policy.start_date,
            policy.end_date,
            policy.policy_number,
            None,
            policy.status,
            None,
            "Not Contacted",
            None,
            "Open",
            None,
            None,
            None,
            created_at,
            created_at,
        ),
    )
    async with db.execute("SELECT last_insert_rowid()") as cur:
        new_pid = int((await cur.fetchone())[0])

    await insert_empty_policy_detail(db, new_pid, it_id)
    await db.commit()

    async with db.execute(
        f"{POLICY_SELECT} WHERE p.policy_id = ?",
        (new_pid,),
    ) as cursor:
        row = await cursor.fetchone()
    return policy_row_to_model(dict(row))


@router.get("/policies/{policy_id}", response_model=Policy)
async def get_policy(
    policy_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific policy."""
    pid = parse_policy_id(policy_id)
    async with db.execute(
        f"{POLICY_SELECT} WHERE p.policy_id = ? AND cu.user_id = ?",
        (pid, user.user_id),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy_row_to_model(dict(row))


@router.get("/policies/{policy_id}/detail", response_model=PolicyDetailBundle)
async def get_policy_detail_bundle(
    policy_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Read-only: policy, customer, category group, and motor/health/property rows when present."""
    pid = parse_policy_id(policy_id)

    async with db.execute(
        f"{POLICY_SELECT} WHERE p.policy_id = ? AND cu.user_id = ?",
        (pid, user.user_id),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy = policy_row_to_model(dict(row))
    cid = int(row["customer_id"])

    async with db.execute(
        f"{CUSTOMER_SELECT} WHERE c.customer_id = ? AND c.user_id = ?",
        (cid, user.user_id),
    ) as cur:
        crow = await cur.fetchone()
    if not crow:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer = customer_row_to_model(dict(crow))

    async with db.execute(
        """SELECT it.category_group FROM policies p
           JOIN insurance_types it ON p.insurance_type_id = it.insurance_type_id
           WHERE p.policy_id = ?""",
        (pid,),
    ) as cur:
        cg_row = await cur.fetchone()
    category_group = (cg_row[0] if cg_row else "Motor") or "Motor"

    motor = await _load_motor_details(db, pid)
    health = await _load_health_details(db, pid)
    property_detail = await _load_property_details(db, pid)

    return PolicyDetailBundle(
        policy=policy,
        customer=customer,
        category_group=category_group,
        motor=motor,
        health=health,
        property_detail=property_detail,
    )


async def _load_motor_details(db, pid: int):
    async with db.execute(
        """SELECT vehicle_no, vehicle_details, idv_of_vehicle, engine_no, chassis_no,
                  od_premium, tp_premium
           FROM motor_policy_details WHERE policy_id = ?""",
        (pid,),
    ) as cur:
        m = await cur.fetchone()
    if not m:
        return None
    md = dict(m)
    return MotorPolicyDetailsDto(
        vehicle_no=md.get("vehicle_no"),
        vehicle_details=md.get("vehicle_details"),
        idv_of_vehicle=sql_float(md.get("idv_of_vehicle")),
        engine_no=md.get("engine_no"),
        chassis_no=md.get("chassis_no"),
        od_premium=sql_float(md.get("od_premium")),
        tp_premium=sql_float(md.get("tp_premium")),
    )


async def _load_health_details(db, pid: int):
    async with db.execute(
        """SELECT plan_name, sum_insured, cover_type, members_covered,
                  base_premium, additional_premium
           FROM health_policy_details WHERE policy_id = ?""",
        (pid,),
    ) as cur:
        h = await cur.fetchone()
    if not h:
        return None
    hd = dict(h)
    return HealthPolicyDetailsDto(
        plan_name=hd.get("plan_name"),
        sum_insured=sql_float(hd.get("sum_insured")),
        cover_type=hd.get("cover_type"),
        members_covered=hd.get("members_covered"),
        base_premium=sql_float(hd.get("base_premium")),
        additional_premium=sql_float(hd.get("additional_premium")),
    )


async def _load_property_details(db, pid: int):
    async with db.execute(
        """SELECT product_name, sum_insured, sub_product, risk_location,
                  base_premium, additional_premium
           FROM property_policy_details WHERE policy_id = ?""",
        (pid,),
    ) as cur:
        pr = await cur.fetchone()
    if not pr:
        return None
    pd = dict(pr)
    return PropertyPolicyDetailsDto(
        product_name=pd.get("product_name"),
        sum_insured=sql_float(pd.get("sum_insured")),
        sub_product=pd.get("sub_product"),
        risk_location=pd.get("risk_location"),
        base_premium=sql_float(pd.get("base_premium")),
        additional_premium=sql_float(pd.get("additional_premium")),
    )


@router.put("/policies/{policy_id}", response_model=Policy)
async def update_policy(
    policy_id: str,
    policy: PolicyCreate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a policy."""
    pid = parse_policy_id(policy_id)

    async with db.execute(
        f"""SELECT p.policy_id FROM policies p
            JOIN customers cu ON p.customer_id = cu.customer_id
            WHERE p.policy_id = ? AND cu.user_id = ?""",
        (pid, user.user_id),
    ) as cursor:
        existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found")

    try:
        cust_pk = int(policy.customer_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Customer not found")

    async with db.execute(
        "SELECT customer_id FROM customers WHERE customer_id = ? AND user_id = ?",
        (cust_pk, user.user_id),
    ) as cur:
        if not await cur.fetchone():
            raise HTTPException(status_code=404, detail="Customer not found")

    it_id = await resolve_insurance_type_id(db, policy.policy_type)
    pay_id = await default_payment_status_id(db)
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """UPDATE policies SET customer_id = ?, insurance_type_id = ?, policy_no = ?,
           total_premium = ?, payment_status_id = ?, date_of_issue = ?, policy_end_date = ?,
           status = ?, updated_at = ?
           WHERE policy_id = ?""",
        (
            cust_pk,
            it_id,
            policy.policy_number,
            policy.premium,
            pay_id,
            policy.start_date,
            policy.end_date,
            policy.status,
            now,
            pid,
        ),
    )
    await db.commit()

    async with db.execute(
        f"{POLICY_SELECT} WHERE p.policy_id = ?",
        (pid,),
    ) as cursor:
        row = await cursor.fetchone()
    return policy_row_to_model(dict(row))


@router.patch("/policies/{policy_id}/contact", response_model=Policy)
async def patch_policy_contact(
    policy_id: str,
    body: PolicyContactUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update renewal contact fields only (last_contacted_at, contact_status, follow_up_date)."""
    pid = parse_policy_id(policy_id)

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "contact_status" in patch and patch["contact_status"] is not None:
        if patch["contact_status"] not in ALLOWED_POLICY_CONTACT_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"contact_status must be one of: {sorted(ALLOWED_POLICY_CONTACT_STATUSES)}",
            )

    async with db.execute(
        f"""SELECT p.policy_id FROM policies p
            JOIN customers cu ON p.customer_id = cu.customer_id
            WHERE p.policy_id = ? AND cu.user_id = ?""",
        (pid, user.user_id),
    ) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Policy not found")

    sets: list[str] = []
    params: list = []
    if "last_contacted_at" in patch:
        sets.append("last_contacted_at = ?")
        params.append(patch["last_contacted_at"])
    if "contact_status" in patch:
        sets.append("contact_status = ?")
        params.append(patch["contact_status"])
    if "follow_up_date" in patch:
        sets.append("follow_up_date = ?")
        params.append(patch["follow_up_date"])

    now = datetime.now(timezone.utc).isoformat()
    sets.append("updated_at = ?")
    params.append(now)
    params.append(pid)

    await db.execute(
        f"UPDATE policies SET {', '.join(sets)} WHERE policy_id = ?",
        tuple(params),
    )
    await db.commit()

    async with db.execute(
        f"{POLICY_SELECT} WHERE p.policy_id = ?",
        (pid,),
    ) as cursor:
        row = await cursor.fetchone()
    return policy_row_to_model(dict(row))


@router.patch("/policies/{policy_id}/payment", response_model=Policy)
async def patch_policy_payment(
    policy_id: str,
    body: PolicyPaymentUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update payment status when current status is PENDING (e.g. mark paid channel)."""
    pid = parse_policy_id(policy_id)

    new_label = (body.payment_status or "").strip()
    if new_label not in ALLOWED_PAYMENT_UPDATE_FROM_PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"payment_status must be one of: {sorted(ALLOWED_PAYMENT_UPDATE_FROM_PENDING)}",
        )

    note = (body.payment_note or "").strip() or None
    now = datetime.now(timezone.utc).isoformat()

    async with db.execute(
        f"""SELECT ps.status_name AS payment_status
            FROM policies p
            JOIN customers cu ON p.customer_id = cu.customer_id
            LEFT JOIN payment_statuses ps ON p.payment_status_id = ps.payment_status_id
            WHERE p.policy_id = ? AND cu.user_id = ?""",
        (pid, user.user_id),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Policy not found")

    current = row["payment_status"]
    if not is_pending_payment_label(current):
        raise HTTPException(
            status_code=400,
            detail="Payment can only be updated from PENDING in this workflow.",
        )

    new_id = await payment_status_id_by_name(db, new_label)
    if new_id is None:
        await db.execute(
            "INSERT INTO payment_statuses (status_name) VALUES (?)",
            (new_label,),
        )
        new_id = await payment_status_id_by_name(db, new_label)

    await db.execute(
        """UPDATE policies SET payment_status_id = ?, payment_note = ?,
               payment_updated_at = ?, updated_at = ?
           WHERE policy_id = ?""",
        (new_id, note, now, now, pid),
    )
    await db.commit()

    async with db.execute(
        f"{POLICY_SELECT} WHERE p.policy_id = ?",
        (pid,),
    ) as cursor:
        out = await cursor.fetchone()
    return policy_row_to_model(dict(out))


@router.patch("/policies/{policy_id}/renewal-resolution", response_model=Policy)
async def patch_policy_renewal_resolution(
    policy_id: str,
    body: PolicyRenewalResolutionUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Set renewal resolution for expired / missed-opportunity workflow. Records stay in DB."""
    pid = parse_policy_id(policy_id)

    if body.renewal_status not in ALLOWED_RENEWAL_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"renewal_status must be one of: {sorted(ALLOWED_RENEWAL_STATUSES)}",
        )

    note = (body.renewal_resolution_note or "").strip() or None
    now = datetime.now(timezone.utc).isoformat()

    async with db.execute(
        f"""SELECT p.policy_id FROM policies p
            JOIN customers cu ON p.customer_id = cu.customer_id
            WHERE p.policy_id = ? AND cu.user_id = ?""",
        (pid, user.user_id),
    ) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Policy not found")

    if body.renewal_status == "Open":
        await db.execute(
            """UPDATE policies SET renewal_status = ?, renewal_resolution_note = ?,
               renewal_resolved_at = NULL, renewal_resolved_by = NULL, updated_at = ?
               WHERE policy_id = ?""",
            ("Open", note, now, pid),
        )
    else:
        await db.execute(
            """UPDATE policies SET renewal_status = ?, renewal_resolution_note = ?,
               renewal_resolved_at = ?, renewal_resolved_by = ?, updated_at = ?
               WHERE policy_id = ?""",
            (body.renewal_status, note, now, user.user_id, now, pid),
        )
    await db.commit()

    async with db.execute(
        f"{POLICY_SELECT} WHERE p.policy_id = ?",
        (pid,),
    ) as cursor:
        row = await cursor.fetchone()
    return policy_row_to_model(dict(row))


@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a policy."""
    pid = parse_policy_id(policy_id)
    await db.execute(
        """DELETE FROM policies WHERE policy_id = ?
           AND EXISTS (
             SELECT 1 FROM customers c
             WHERE c.customer_id = policies.customer_id AND c.user_id = ?
           )""",
        (pid, user.user_id),
    )
    await db.commit()
    return {"message": "Policy deleted successfully"}
