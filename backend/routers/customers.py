"""Customer CRUD endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from deps import get_current_user, get_db
from repositories.sql import (
    CUSTOMER_SELECT,
    customer_row_to_model,
    parse_customer_id,
)
from schemas import Customer, CustomerCreate, User

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
