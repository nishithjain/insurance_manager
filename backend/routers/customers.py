"""Customer CRUD endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query

from deps import get_current_user, get_db, require_admin
from repositories.sql import (
    CUSTOMER_ADMIN_SELECT,
    CUSTOMER_SELECT,
    customer_admin_row_to_model,
    customer_row_to_model,
    parse_customer_id,
)
from schemas import Customer, CustomerAdmin, CustomerAdminUpdate, CustomerCreate, User

router = APIRouter(tags=["customers"])


@router.get("/customers", response_model=List[Customer])
async def get_customers(
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all customers for current user."""
    async with db.execute(
        f"{CUSTOMER_SELECT} WHERE c.user_id = ? ORDER BY c.created_at DESC",
        (user.user_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [customer_row_to_model(dict(row)) for row in rows]


@router.post("/customers", response_model=Customer)
async def create_customer(
    customer: CustomerCreate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new customer."""
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO customers (user_id, full_name, email, phone_number, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user.user_id, customer.name, customer.email, customer.phone, now, now),
    )
    async with db.execute("SELECT last_insert_rowid()") as cur:
        cid = int((await cur.fetchone())[0])

    if customer.address and str(customer.address).strip():
        await db.execute(
            """INSERT INTO customer_addresses (
                 customer_id, raw_address, country, created_at, updated_at
               ) VALUES (?, ?, 'India', ?, ?)""",
            (cid, str(customer.address).strip(), now, now),
        )

    await db.commit()

    async with db.execute(
        f"{CUSTOMER_SELECT} WHERE c.customer_id = ?",
        (cid,),
    ) as cursor:
        row = await cursor.fetchone()

    return customer_row_to_model(dict(row))


@router.get("/customers/{customer_id}", response_model=Customer)
async def get_customer(
    customer_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific customer."""
    cid = parse_customer_id(customer_id)
    async with db.execute(
        f"{CUSTOMER_SELECT} WHERE c.customer_id = ? AND c.user_id = ?",
        (cid, user.user_id),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer_row_to_model(dict(row))


@router.put("/customers/{customer_id}", response_model=Customer)
async def update_customer(
    customer_id: str,
    customer: CustomerCreate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a customer."""
    cid = parse_customer_id(customer_id)

    async with db.execute(
        "SELECT customer_id FROM customers WHERE customer_id = ? AND user_id = ?",
        (cid, user.user_id),
    ) as cursor:
        existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Customer not found")

    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """UPDATE customers SET full_name = ?, email = ?, phone_number = ?, updated_at = ?
           WHERE customer_id = ? AND user_id = ?""",
        (customer.name, customer.email, customer.phone, now, cid, user.user_id),
    )

    async with db.execute(
        "SELECT address_id FROM customer_addresses WHERE customer_id = ? ORDER BY address_id LIMIT 1",
        (cid,),
    ) as cur:
        addr_row = await cur.fetchone()

    addr_text = (customer.address or "").strip() or None
    if addr_row:
        await db.execute(
            "UPDATE customer_addresses SET raw_address = ?, updated_at = ? WHERE address_id = ?",
            (addr_text, now, addr_row[0]),
        )
    elif addr_text:
        await db.execute(
            """INSERT INTO customer_addresses (
                 customer_id, raw_address, country, created_at, updated_at
               ) VALUES (?, ?, 'India', ?, ?)""",
            (cid, addr_text, now, now),
        )

    await db.commit()

    async with db.execute(
        f"{CUSTOMER_SELECT} WHERE c.customer_id = ?",
        (cid,),
    ) as cursor:
        row = await cursor.fetchone()

    return customer_row_to_model(dict(row))


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a customer."""
    cid = parse_customer_id(customer_id)
    await db.execute(
        "DELETE FROM customers WHERE customer_id = ? AND user_id = ?",
        (cid, user.user_id),
    )
    await db.commit()
    return {"message": "Customer deleted successfully"}


# --------------------------------------------------------------------------- #
# Admin-only customer management                                              #
#                                                                             #
# These endpoints are mounted under ``/api/admin/customers`` and gated by     #
# :func:`deps.require_admin`. They are intentionally NOT scoped to a single   #
# data-owner ``user_id`` — admins manage every customer record, while the     #
# above per-user routes remain the contract used by the mobile app and the   #
# non-admin web flows.                                                        #
# --------------------------------------------------------------------------- #


@router.get("/admin/customers", response_model=List[CustomerAdmin])
async def admin_list_customers(
    search: Optional[str] = Query(default=None, max_length=200),
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
):
    """
    List every customer (with policy_count) for the admin grid.

    ``search`` is a single text token applied case-insensitively against
    name / email / phone / address / policy_no — a free-text box on the UI
    side maps to one server query, no flag plumbing required.
    """
    where = ""
    params: list = []
    q = (search or "").strip()
    if q:
        like = f"%{q}%"
        where = (
            " WHERE c.full_name LIKE ? COLLATE NOCASE"
            " OR c.email LIKE ? COLLATE NOCASE"
            " OR c.phone_number LIKE ? COLLATE NOCASE"
            " OR EXISTS (SELECT 1 FROM customer_addresses a"
            "            WHERE a.customer_id = c.customer_id"
            "              AND a.raw_address LIKE ? COLLATE NOCASE)"
            " OR EXISTS (SELECT 1 FROM policies p"
            "            WHERE p.customer_id = c.customer_id"
            "              AND p.policy_no LIKE ? COLLATE NOCASE)"
        )
        params.extend([like, like, like, like, like])

    sql = (
        f"{CUSTOMER_ADMIN_SELECT}{where}"
        " ORDER BY c.created_at DESC, c.customer_id DESC"
        " LIMIT ? OFFSET ?"
    )
    params.extend([int(limit), int(offset)])
    async with db.execute(sql, tuple(params)) as cursor:
        rows = await cursor.fetchall()
    return [customer_admin_row_to_model(dict(row)) for row in rows]


@router.get("/admin/customers/{customer_id}", response_model=CustomerAdmin)
async def admin_get_customer(
    customer_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
):
    cid = parse_customer_id(customer_id)
    async with db.execute(
        f"{CUSTOMER_ADMIN_SELECT} WHERE c.customer_id = ?",
        (cid,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer_admin_row_to_model(dict(row))


@router.put("/admin/customers/{customer_id}", response_model=CustomerAdmin)
async def admin_update_customer(
    customer_id: str,
    payload: CustomerAdminUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
):
    """
    Update a customer regardless of which data-owner owns the row.

    Mirrors the per-user :func:`update_customer` write path (customers table +
    optional first-row in customer_addresses), without the ``user_id`` filter.
    """
    cid = parse_customer_id(customer_id)
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Customer name is required.")

    async with db.execute(
        "SELECT customer_id FROM customers WHERE customer_id = ?",
        (cid,),
    ) as cursor:
        existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Customer not found")

    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """UPDATE customers SET full_name = ?, email = ?, phone_number = ?, updated_at = ?
           WHERE customer_id = ?""",
        (name, payload.email, payload.phone, now, cid),
    )

    async with db.execute(
        "SELECT address_id FROM customer_addresses WHERE customer_id = ? ORDER BY address_id LIMIT 1",
        (cid,),
    ) as cur:
        addr_row = await cur.fetchone()

    addr_text = (payload.address or "").strip() or None
    if addr_row:
        await db.execute(
            "UPDATE customer_addresses SET raw_address = ?, updated_at = ? WHERE address_id = ?",
            (addr_text, now, addr_row[0]),
        )
    elif addr_text:
        await db.execute(
            """INSERT INTO customer_addresses (
                 customer_id, raw_address, country, created_at, updated_at
               ) VALUES (?, ?, 'India', ?, ?)""",
            (cid, addr_text, now, now),
        )

    await db.commit()

    async with db.execute(
        f"{CUSTOMER_ADMIN_SELECT} WHERE c.customer_id = ?",
        (cid,),
    ) as cursor:
        row = await cursor.fetchone()
    return customer_admin_row_to_model(dict(row))
