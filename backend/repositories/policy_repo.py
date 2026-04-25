"""
SQL fragments, row→schema mappers, and stub-row inserts for the ``policies``
table and its per-line-of-business detail tables.
"""

from __future__ import annotations

import aiosqlite

from schemas import Policy

from ._helpers import maybe_int


# Shape used by the read APIs (``GET /api/policies``, single-policy read,
# expiry/recent lists). Includes the new two-layer taxonomy joins so a Policy
# response carries both the legacy ``policy_type`` text and the new
# ``insurance_type_*`` / ``policy_type_*`` ids/names.
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
        p.renewal_resolved_by AS renewal_resolved_by,
        pt.id AS policy_type_id,
        pt.name AS policy_type_name,
        ic.id AS insurance_type_id,
        COALESCE(ic.name, it.category_group) AS insurance_type_name
    FROM policies p
    JOIN customers cu ON p.customer_id = cu.customer_id
    JOIN insurance_types it ON p.insurance_type_id = it.insurance_type_id
    LEFT JOIN companies co ON p.company_id = co.company_id
    LEFT JOIN payment_statuses ps ON p.payment_status_id = ps.payment_status_id
    LEFT JOIN policy_types pt ON p.policy_type_id = pt.id
    LEFT JOIN insurance_categories ic
        ON ic.id = pt.insurance_category_id
        OR (pt.insurance_category_id IS NULL
            AND ic.name = it.category_group COLLATE NOCASE)
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


def policy_row_to_model(row: dict) -> Policy:
    """Materialize a :data:`POLICY_SELECT` row into a :class:`Policy`."""
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
        insurance_type_id=maybe_int(row.get("insurance_type_id")),
        insurance_type_name=row.get("insurance_type_name"),
        policy_type_id=maybe_int(row.get("policy_type_id")),
        policy_type_name=row.get("policy_type_name"),
    )


# --------------------------------------------------------------------------- #
# Existence / authorisation lookups                                           #
# --------------------------------------------------------------------------- #


async def policy_exists_for_user(
    db: aiosqlite.Connection, policy_id: int, user_id: str
) -> bool:
    """Return True iff the policy belongs to the data-owner of ``user_id``."""
    async with db.execute(
        """SELECT 1 FROM policies p
           JOIN customers cu ON p.customer_id = cu.customer_id
           WHERE p.policy_id = ? AND cu.user_id = ? LIMIT 1""",
        (policy_id, user_id),
    ) as cur:
        return await cur.fetchone() is not None


async def customer_exists_for_user(
    db: aiosqlite.Connection, customer_pk: int, user_id: str
) -> bool:
    """Return True iff the customer is owned by ``user_id``."""
    async with db.execute(
        "SELECT 1 FROM customers WHERE customer_id = ? AND user_id = ? LIMIT 1",
        (customer_pk, user_id),
    ) as cur:
        return await cur.fetchone() is not None


async def get_payment_status_label_for_user(
    db: aiosqlite.Connection, policy_id: int, user_id: str
) -> tuple[bool, str | None]:
    """
    Look up the current payment-status label (e.g. ``PENDING`` / ``PAID``)
    for a policy, scoped to ``user_id``.

    Returns ``(found, label)`` so callers can distinguish "policy not found"
    (404) from "policy found but no payment-status row" (label is None,
    legacy data).
    """
    async with db.execute(
        """SELECT ps.status_name AS payment_status
           FROM policies p
           JOIN customers cu ON p.customer_id = cu.customer_id
           LEFT JOIN payment_statuses ps ON p.payment_status_id = ps.payment_status_id
           WHERE p.policy_id = ? AND cu.user_id = ?""",
        (policy_id, user_id),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return False, None
    return True, row["payment_status"]


# --------------------------------------------------------------------------- #
# Read helpers                                                                #
# --------------------------------------------------------------------------- #


async def fetch_policy_model(
    db: aiosqlite.Connection, policy_id: int
) -> Policy | None:
    """Re-read a policy by id and materialize it. Used after every write."""
    async with db.execute(
        f"{POLICY_SELECT} WHERE p.policy_id = ?",
        (policy_id,),
    ) as cur:
        row = await cur.fetchone()
    return policy_row_to_model(dict(row)) if row else None


async def list_policy_models_for_user(
    db: aiosqlite.Connection, user_id: str
) -> list[Policy]:
    """All policies owned by ``user_id``, newest first."""
    async with db.execute(
        f"{POLICY_SELECT} WHERE cu.user_id = ? ORDER BY p.created_at DESC",
        (user_id,),
    ) as cur:
        rows = await cur.fetchall()
    return [policy_row_to_model(dict(r)) for r in rows]


async def fetch_policy_model_for_user(
    db: aiosqlite.Connection, policy_id: int, user_id: str
) -> tuple[Policy | None, int | None]:
    """
    Combined "fetch and authorize" used by the read APIs.

    Returns ``(policy, customer_pk)``; when the row doesn't exist or is owned
    by a different user, both come back as ``None`` so the caller can raise
    a single 404.
    """
    async with db.execute(
        f"{POLICY_SELECT} WHERE p.policy_id = ? AND cu.user_id = ?",
        (policy_id, user_id),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return None, None
    return policy_row_to_model(dict(row)), int(row["customer_id"])


# --------------------------------------------------------------------------- #
# Inserts / updates                                                           #
# --------------------------------------------------------------------------- #


async def insert_policy(
    db: aiosqlite.Connection,
    *,
    source_record_id: str,
    customer_pk: int,
    insurance_type_id: int,
    policy_type_id: int | None,
    premium: float,
    payment_status_id: int | None,
    start_date: str,
    end_date: str,
    policy_number: str,
    status: str,
    created_at: str,
) -> int:
    """Insert a new policy row and return the new ``policy_id``."""
    await db.execute(
        """INSERT INTO policies (
            source_record_id, customer_id, address_id, insurance_type_id,
            company_id, agent_id, ncb_discount, total_premium, payment_status_id,
            date_of_issue, policy_end_date, policy_no, card_details, status,
            last_contacted_at, contact_status, follow_up_date,
            renewal_status, renewal_resolution_note, renewal_resolved_at, renewal_resolved_by,
            policy_type_id,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            source_record_id,
            customer_pk,
            None,
            insurance_type_id,
            None,
            None,
            None,
            premium,
            payment_status_id,
            start_date,
            end_date,
            policy_number,
            None,
            status,
            None,
            "Not Contacted",
            None,
            "Open",
            None,
            None,
            None,
            policy_type_id,
            created_at,
            created_at,
        ),
    )
    async with db.execute("SELECT last_insert_rowid()") as cur:
        return int((await cur.fetchone())[0])


async def update_policy_core(
    db: aiosqlite.Connection,
    policy_id: int,
    *,
    customer_pk: int,
    insurance_type_id: int,
    policy_type_id: int | None,
    overwrite_policy_type_id: bool,
    policy_number: str,
    premium: float,
    payment_status_id: int | None,
    start_date: str,
    end_date: str,
    status: str,
    now: str,
) -> None:
    """
    Update the core columns of a policy row.

    ``overwrite_policy_type_id`` toggles whether the new ``policy_type_id``
    is included in the UPDATE — set to ``False`` for legacy clients that
    don't send a value, so a previously-set FK is preserved.
    """
    if overwrite_policy_type_id:
        await db.execute(
            """UPDATE policies SET customer_id = ?, insurance_type_id = ?,
                  policy_type_id = ?, policy_no = ?,
                  total_premium = ?, payment_status_id = ?, date_of_issue = ?,
                  policy_end_date = ?, status = ?, updated_at = ?
               WHERE policy_id = ?""",
            (
                customer_pk,
                insurance_type_id,
                policy_type_id,
                policy_number,
                premium,
                payment_status_id,
                start_date,
                end_date,
                status,
                now,
                policy_id,
            ),
        )
    else:
        await db.execute(
            """UPDATE policies SET customer_id = ?, insurance_type_id = ?, policy_no = ?,
               total_premium = ?, payment_status_id = ?, date_of_issue = ?, policy_end_date = ?,
               status = ?, updated_at = ?
               WHERE policy_id = ?""",
            (
                customer_pk,
                insurance_type_id,
                policy_number,
                premium,
                payment_status_id,
                start_date,
                end_date,
                status,
                now,
                policy_id,
            ),
        )


async def update_policy_contact_fields(
    db: aiosqlite.Connection,
    policy_id: int,
    patch: dict,
    now: str,
) -> None:
    """Apply a partial PATCH over the renewal-contact columns."""
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
    sets.append("updated_at = ?")
    params.append(now)
    params.append(policy_id)

    await db.execute(
        f"UPDATE policies SET {', '.join(sets)} WHERE policy_id = ?",
        tuple(params),
    )


async def update_policy_payment(
    db: aiosqlite.Connection,
    policy_id: int,
    *,
    payment_status_id: int,
    note: str | None,
    now: str,
) -> None:
    """Set payment status, note, and the audit timestamps."""
    await db.execute(
        """UPDATE policies SET payment_status_id = ?, payment_note = ?,
               payment_updated_at = ?, updated_at = ?
           WHERE policy_id = ?""",
        (payment_status_id, note, now, now, policy_id),
    )


async def update_policy_renewal_resolution(
    db: aiosqlite.Connection,
    policy_id: int,
    *,
    status: str,
    note: str | None,
    now: str,
    resolved_by: str | None,
) -> None:
    """
    Set or clear the renewal-resolution columns.

    When ``status == "Open"`` we explicitly NULL out ``renewal_resolved_at``
    and ``renewal_resolved_by`` so reopening a previously-closed renewal
    leaves a clean state.
    """
    if status == "Open":
        await db.execute(
            """UPDATE policies SET renewal_status = ?, renewal_resolution_note = ?,
               renewal_resolved_at = NULL, renewal_resolved_by = NULL, updated_at = ?
               WHERE policy_id = ?""",
            ("Open", note, now, policy_id),
        )
    else:
        await db.execute(
            """UPDATE policies SET renewal_status = ?, renewal_resolution_note = ?,
               renewal_resolved_at = ?, renewal_resolved_by = ?, updated_at = ?
               WHERE policy_id = ?""",
            (status, note, now, resolved_by, now, policy_id),
        )


async def delete_policy_for_user(
    db: aiosqlite.Connection, policy_id: int, user_id: str
) -> None:
    """Delete a policy iff it belongs to ``user_id``. Silent no-op otherwise."""
    await db.execute(
        """DELETE FROM policies WHERE policy_id = ?
           AND EXISTS (
             SELECT 1 FROM customers c
             WHERE c.customer_id = policies.customer_id AND c.user_id = ?
           )""",
        (policy_id, user_id),
    )


async def insert_empty_policy_detail(
    db: aiosqlite.Connection, policy_id: int, insurance_type_id: int
) -> None:
    """
    Insert a stub row into motor / health / property detail tables based on
    the legacy ``insurance_types.category_group``.

    Categories without a per-LOB detail table (Life, Travel, ...) are skipped
    intentionally — the policy itself still saves cleanly with no detail row,
    matching the existing behavior for unknown groups.
    """
    async with db.execute(
        "SELECT category_group FROM insurance_types WHERE insurance_type_id = ?",
        (insurance_type_id,),
    ) as cur:
        row = await cur.fetchone()
    cat = ((row[0] if row else "Motor") or "Motor").strip()
    if cat == "Motor":
        await db.execute(
            "INSERT INTO motor_policy_details (policy_id) VALUES (?)", (policy_id,)
        )
    elif cat == "Health":
        await db.execute(
            "INSERT INTO health_policy_details (policy_id) VALUES (?)", (policy_id,)
        )
    elif cat == "Property":
        await db.execute(
            "INSERT INTO property_policy_details (policy_id) VALUES (?)", (policy_id,)
        )
    # Life / Travel: no per-LOB detail row — handled in policies row alone.
