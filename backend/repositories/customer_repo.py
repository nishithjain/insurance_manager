"""
SQL fragments and row→schema mappers for the ``customers`` table.

Two SELECT shapes coexist here intentionally:

* :data:`CUSTOMER_SELECT` — the per-user mobile/web shape (``Customer``
  schema). Untouched by the admin grid feature.
* :data:`CUSTOMER_ADMIN_SELECT` — admin-only shape with ``updated_at`` and
  the correlated ``policy_count`` column the admin UI surfaces.
"""

from __future__ import annotations

from schemas import Customer, CustomerAdmin


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


CUSTOMER_ADMIN_SELECT = """
    SELECT
        c.customer_id AS id,
        c.user_id,
        c.full_name AS name,
        c.email,
        c.phone_number AS phone,
        (SELECT raw_address FROM customer_addresses a
         WHERE a.customer_id = c.customer_id ORDER BY a.address_id LIMIT 1) AS address,
        c.created_at,
        c.updated_at,
        (SELECT COUNT(1) FROM policies p WHERE p.customer_id = c.customer_id) AS policy_count
    FROM customers c
"""


def customer_row_to_model(row: dict) -> Customer:
    """Materialize a :data:`CUSTOMER_SELECT` row into a :class:`Customer`."""
    return Customer(
        id=str(row["id"]),
        user_id=row["user_id"],
        name=row["name"] or "",
        email=row.get("email"),
        phone=row.get("phone"),
        address=row.get("address"),
        created_at=row["created_at"] or "",
    )


def customer_admin_row_to_model(row: dict) -> CustomerAdmin:
    """Materialize a :data:`CUSTOMER_ADMIN_SELECT` row into :class:`CustomerAdmin`."""
    pc = row.get("policy_count")
    try:
        pc = int(pc) if pc is not None else 0
    except (TypeError, ValueError):
        pc = 0
    return CustomerAdmin(
        id=str(row["id"]),
        user_id=row["user_id"],
        name=row["name"] or "",
        email=row.get("email"),
        phone=row.get("phone"),
        address=row.get("address"),
        created_at=row["created_at"] or "",
        updated_at=row.get("updated_at"),
        policy_count=pc,
    )


# --------------------------------------------------------------------------- #
# Customer contact updates (used by the policy edit modal)                    #
# --------------------------------------------------------------------------- #


def _normalize_optional(value) -> str | None:
    """Trim a string, returning None when empty so SQL stores NULL."""
    return ((value or "").strip() or None) if isinstance(value, str) else value


async def update_customer_contact_fields(
    db,
    customer_pk: int,
    patch: dict,
    now: str,
) -> None:
    """
    Apply a partial PATCH over the customer's contact columns.

    The ``patch`` dict is the output of
    ``PolicyUpdateCustomerFields.model_dump(exclude_unset=True)`` — only keys
    actually sent by the client are present, so we know which columns to
    overwrite vs. leave alone.

    The address is intentionally NOT handled here: it lives in
    ``customer_addresses`` and has its own upsert helper.
    """
    sets: list[str] = []
    params: list = []
    if "email" in patch:
        sets.append("email = ?")
        params.append(_normalize_optional(patch["email"]))
    if "phone" in patch:
        sets.append("phone_number = ?")
        params.append(_normalize_optional(patch["phone"]))

    if not sets:
        return

    sets.append("updated_at = ?")
    params.append(now)
    params.append(customer_pk)
    await db.execute(
        f"UPDATE customers SET {', '.join(sets)} WHERE customer_id = ?",
        tuple(params),
    )


async def upsert_customer_address(
    db,
    customer_pk: int,
    raw_address: str | None,
    now: str,
) -> None:
    """
    Insert-or-update the customer's primary address row.

    We always target the lowest-id address row (matches the ``CUSTOMER_SELECT``
    ordering used everywhere else). When no row exists yet and a non-empty
    address is provided, we INSERT a new one with ``country='India'`` to
    match the legacy default. When the new value is empty/None and no row
    exists, we leave well enough alone.
    """
    addr_text = _normalize_optional(raw_address)
    async with db.execute(
        """SELECT address_id FROM customer_addresses
           WHERE customer_id = ? ORDER BY address_id LIMIT 1""",
        (customer_pk,),
    ) as cur:
        addr_row = await cur.fetchone()
    if addr_row:
        await db.execute(
            """UPDATE customer_addresses
               SET raw_address = ?, updated_at = ?
               WHERE address_id = ?""",
            (addr_text, now, addr_row[0]),
        )
    elif addr_text:
        await db.execute(
            """INSERT INTO customer_addresses (
                 customer_id, raw_address, country, created_at, updated_at
               ) VALUES (?, ?, 'India', ?, ?)""",
            (customer_pk, addr_text, now, now),
        )
