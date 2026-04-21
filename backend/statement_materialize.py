"""
Turn rows in statement_policy_lines (from MARCH STATEMENTS CSV import) into
customers, addresses, policies, and motor_policy_details for a given user_id.

CSV import only fills statement_policy_lines; this step links data to the normalized model.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from statement_parse import split_name_address


def _customer_name_and_address(row: dict[str, Any]) -> Tuple[str, Optional[str]]:
    cn = (row.get("customer_name") or "").strip()
    if cn:
        raw = row.get("address")
        if raw is None:
            return cn[:200], None
        s = str(raw).strip()
        return cn[:200], (s if s else None)
    legacy = row.get("name_and_address")
    return split_name_address(legacy if legacy else None)


def _norm_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return None
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def _parse_iso_date_dd_mm_yyyy(s: Optional[str]) -> str:
    s = (s or "").strip()
    if not s:
        return datetime.now(timezone.utc).date().isoformat()
    m = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", s)
    if m:
        d, mo, y = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return datetime.now(timezone.utc).date().isoformat()


def _parse_premium(s: Optional[str]) -> float:
    if not s:
        return 0.0
    t = re.sub(r"[^\d.]", "", str(s).replace(",", ""))
    try:
        return float(t) if t else 0.0
    except ValueError:
        return 0.0


def _policy_no(row: dict[str, Any]) -> str:
    raw = (row.get("policy_number") or "").strip()
    if raw:
        return raw.replace("\n", " ")[:200]
    return ""


async def _motor_type_id(db: Any) -> int:
    async with db.execute(
        """SELECT insurance_type_id FROM insurance_types
           WHERE category_group = 'Motor' ORDER BY insurance_type_id LIMIT 1"""
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise RuntimeError("No Motor insurance_type in insurance_types (seed failed)")
    return row[0]


async def _get_or_create_company(db: Any, name: Optional[str]) -> Optional[int]:
    if not name or not str(name).strip():
        return None
    n = str(name).strip()[:500]
    async with db.execute("SELECT company_id FROM companies WHERE company_name = ?", (n,)) as cur:
        hit = await cur.fetchone()
    if hit:
        return int(hit[0])
    await db.execute("INSERT INTO companies (company_name) VALUES (?)", (n,))
    async with db.execute("SELECT last_insert_rowid()") as cur:
        return int((await cur.fetchone())[0])


async def _get_or_create_agent(db: Any, name: Optional[str]) -> Optional[int]:
    if not name or not str(name).strip():
        return None
    n = str(name).strip()[:500]
    async with db.execute("SELECT agent_id FROM agents WHERE agent_name = ?", (n,)) as cur:
        hit = await cur.fetchone()
    if hit:
        return int(hit[0])
    await db.execute("INSERT INTO agents (agent_name) VALUES (?)", (n,))
    async with db.execute("SELECT last_insert_rowid()") as cur:
        return int((await cur.fetchone())[0])


async def _get_or_create_payment_status(db: Any, name: Optional[str]) -> Optional[int]:
    label = (name or "").strip() or "Unknown"
    label = label[:200]
    async with db.execute(
        "SELECT payment_status_id FROM payment_statuses WHERE status_name = ?", (label,)
    ) as cur:
        hit = await cur.fetchone()
    if hit:
        return int(hit[0])
    await db.execute("INSERT INTO payment_statuses (status_name) VALUES (?)", (label,))
    async with db.execute("SELECT last_insert_rowid()") as cur:
        return int((await cur.fetchone())[0])


async def _get_or_create_customer(
    db: Any,
    user_id: str,
    name_line: str,
    phone_norm: Optional[str],
    now: str,
) -> Tuple[int, bool]:
    if phone_norm:
        async with db.execute(
            """SELECT customer_id FROM customers
               WHERE user_id = ? AND phone_number = ? LIMIT 1""",
            (user_id, phone_norm),
        ) as cur:
            hit = await cur.fetchone()
        if hit:
            return int(hit[0]), False
    else:
        async with db.execute(
            """SELECT customer_id FROM customers
               WHERE user_id = ? AND full_name = ? LIMIT 1""",
            (user_id, name_line[:200]),
        ) as cur:
            hit = await cur.fetchone()
        if hit:
            return int(hit[0]), False

    await db.execute(
        """INSERT INTO customers (user_id, full_name, email, phone_number, created_at, updated_at)
           VALUES (?, ?, NULL, ?, ?, ?)""",
        (user_id, name_line[:200], phone_norm, now, now),
    )
    async with db.execute("SELECT last_insert_rowid()") as cur:
        cid = int((await cur.fetchone())[0])
    return cid, True


async def materialize_statement_lines(db: Any, user_id: str) -> dict[str, int]:
    """
    Insert customers/policies/motor details for this user from statement_policy_lines (motor CSV).
    Idempotent: skips rows whose source_record_id or (user-scoped) policy_no already exists.
    """
    stats = {
        "statement_rows": 0,
        "customers_created": 0,
        "policies_created": 0,
        "policies_skipped": 0,
    }

    async with db.execute("SELECT COUNT(*) FROM statement_policy_lines") as cur:
        stats["statement_rows"] = (await cur.fetchone())[0]

    async with db.execute("SELECT * FROM statement_policy_lines ORDER BY id") as cur:
        rows = await cur.fetchall()

    now = datetime.now(timezone.utc).isoformat()
    motor_tid = await _motor_type_id(db)

    for row in rows:
        r = dict(row)
        sid = int(r["id"])
        source_record_id = f"stmt-line-{sid}"

        async with db.execute(
            "SELECT policy_id FROM policies WHERE source_record_id = ?", (source_record_id,)
        ) as pc:
            if await pc.fetchone():
                stats["policies_skipped"] += 1
                continue

        pno = _policy_no(r)
        if pno:
            async with db.execute(
                """SELECT p.policy_id FROM policies p
                   JOIN customers c ON p.customer_id = c.customer_id
                   WHERE c.user_id = ? AND p.policy_no = ? LIMIT 1""",
                (user_id, pno),
            ) as pc:
                if await pc.fetchone():
                    stats["policies_skipped"] += 1
                    continue

        name_line, addr = _customer_name_and_address(r)
        phone_norm = _norm_phone(r.get("phone_number"))

        customer_id, created = await _get_or_create_customer(
            db, user_id, name_line, phone_norm, now
        )
        if created:
            stats["customers_created"] += 1

        if addr:
            await db.execute(
                """INSERT INTO customer_addresses (
                     customer_id, raw_address, country, created_at, updated_at
                   ) VALUES (?, ?, 'India', ?, ?)""",
                (customer_id, addr, now, now),
            )
            async with db.execute("SELECT last_insert_rowid()") as cur:
                address_id = int((await cur.fetchone())[0])
        else:
            address_id = None

        company_id = await _get_or_create_company(db, r.get("insurer_company"))
        agent_id = await _get_or_create_agent(db, r.get("agent"))
        pay_id = await _get_or_create_payment_status(db, r.get("payment_status"))

        issue = _parse_iso_date_dd_mm_yyyy(r.get("date_of_issue"))
        end_d = _parse_iso_date_dd_mm_yyyy(r.get("policy_end_date"))
        total_prem = _parse_premium(r.get("premium_total"))
        ncb = (r.get("ncb_or_discount") or "").strip() or None
        card_d = (r.get("card_details") or "").strip() or None
        pol_no_ins = pno or f"stmt-line-{sid}"

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
                customer_id,
                address_id,
                motor_tid,
                company_id,
                agent_id,
                ncb,
                total_prem,
                pay_id,
                issue,
                end_d,
                pol_no_ins,
                card_d,
                "active",
                None,
                "Not Contacted",
                None,
                "Open",
                None,
                None,
                None,
                now,
                now,
            ),
        )
        async with db.execute("SELECT last_insert_rowid()") as cur:
            policy_id = int((await cur.fetchone())[0])

        await db.execute(
            """INSERT INTO motor_policy_details (
                policy_id, vehicle_no, vehicle_details, idv_of_vehicle,
                engine_no, chassis_no, od_premium, tp_premium
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (
                policy_id,
                (r.get("vehicle_registration") or "").strip() or None,
                (r.get("vehicle_details") or "").strip() or None,
                _parse_premium(r.get("idv")) or None,
                (r.get("engine_no") or "").strip() or None,
                (r.get("chassis_no") or "").strip() or None,
                _parse_premium(r.get("od_premium")) or None,
                _parse_premium(r.get("tp_premium")) or None,
            ),
        )
        stats["policies_created"] += 1

    return stats
