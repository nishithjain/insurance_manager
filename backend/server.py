from fastapi import (
    FastAPI,
    APIRouter,
    HTTPException,
    Response,
    Query,
    File,
    Form,
    UploadFile,
)
from fastapi.responses import JSONResponse, StreamingResponse
import sqlite3

from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
from datetime import date, datetime, timezone, timedelta
import uuid
import json
import io
import csv
import re
import zipfile

from db_path import DB_PATH
from database import init_db, get_db
from statement_materialize import materialize_statement_lines
from statement_parse import split_name_address
from import_march_statements import import_csv_from_bytes
from insurance_statistics import build_dashboard_statistics
from policy_export import (
    EXPORT_POLICIES_CSV_HEADERS,
    build_export_row,
    render_split_csv_rows,
    validate_and_summarize_export,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


@app.get("/")
async def site_root():
    """So opening http://host:port/ in a browser is not a 404; API lives under /api."""
    return {
        "message": "Insurance App API",
        "api_base": "/api/",
        "health": "/api/health",
        "docs": "/docs",
    }

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= MODELS =============

class User(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    created_at: str

class Customer(BaseModel):
    id: str
    user_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: str

class CustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class Policy(BaseModel):
    id: str
    user_id: str
    customer_id: str
    policy_number: str
    policy_type: str
    insurer_company: Optional[str] = None
    payment_status: Optional[str] = None
    payment_note: Optional[str] = None
    payment_updated_at: Optional[str] = None
    start_date: str
    end_date: str
    premium: float
    status: str
    created_at: str
    last_contacted_at: Optional[str] = None
    contact_status: str = "Not Contacted"
    follow_up_date: Optional[str] = None
    renewal_status: str = "Open"
    renewal_resolution_note: Optional[str] = None
    renewal_resolved_at: Optional[str] = None
    renewal_resolved_by: Optional[str] = None


class MotorPolicyDetailsDto(BaseModel):
    """Subset of motor_policy_details for mobile read-only detail."""

    vehicle_no: Optional[str] = None
    vehicle_details: Optional[str] = None
    idv_of_vehicle: Optional[float] = None
    engine_no: Optional[str] = None
    chassis_no: Optional[str] = None
    od_premium: Optional[float] = None
    tp_premium: Optional[float] = None


class HealthPolicyDetailsDto(BaseModel):
    """Subset of health_policy_details for mobile read-only detail."""

    plan_name: Optional[str] = None
    sum_insured: Optional[float] = None
    cover_type: Optional[str] = None
    members_covered: Optional[str] = None
    base_premium: Optional[float] = None
    additional_premium: Optional[float] = None


class PropertyPolicyDetailsDto(BaseModel):
    """Subset of property_policy_details for mobile read-only detail."""

    product_name: Optional[str] = None
    sum_insured: Optional[float] = None
    sub_product: Optional[str] = None
    risk_location: Optional[str] = None
    base_premium: Optional[float] = None
    additional_premium: Optional[float] = None


class PolicyDetailBundle(BaseModel):
    """Policy + customer + insurance category + optional line-of-business details."""

    policy: Policy
    customer: Customer
    category_group: str
    motor: Optional[MotorPolicyDetailsDto] = None
    health: Optional[HealthPolicyDetailsDto] = None
    property_detail: Optional[PropertyPolicyDetailsDto] = None


ALLOWED_RENEWAL_STATUSES = frozenset(
    {
        "Open",
        "RenewedWithUs",
        "RenewedElsewhere",
        "NotInterested",
        "PolicyClosed",
        "Duplicate",
    }
)


ALLOWED_POLICY_CONTACT_STATUSES = frozenset(
    {"Not Contacted", "Contacted Today", "Follow-up Needed"}
)


class PolicyContactUpdate(BaseModel):
    """Partial update for renewal contact tracking (PATCH). Omitted fields are left unchanged."""

    last_contacted_at: Optional[str] = None
    contact_status: Optional[str] = None
    follow_up_date: Optional[str] = None


class PolicyRenewalResolutionUpdate(BaseModel):
    """Resolve or reopen expired-policy renewal workflow (PATCH)."""

    renewal_status: str
    renewal_resolution_note: Optional[str] = None


class PolicyPaymentUpdate(BaseModel):
    """Set payment status when clearing a PENDING row (PATCH)."""

    payment_status: str
    payment_note: Optional[str] = None


# Allowed targets when moving off PENDING — extend with new labels in DB + frontend paymentStatus.js
ALLOWED_PAYMENT_UPDATE_FROM_PENDING = frozenset(
    {
        "CUSTOMER ONLINE",
        "CUSTOMER CHEQUE",
        "TRANSFER TO SAMRAJ",
        "CASH TO SAMRAJ",
        "CASH TO SANDESH",
    }
)

PENDING_PAYMENT_STATUS_NAME = "PENDING"


class PolicyCreate(BaseModel):
    customer_id: str
    policy_number: str
    policy_type: str
    start_date: str
    end_date: str
    premium: float
    status: str = "active"


class StatementImportStats(BaseModel):
    """Result of promoting statement_policy_lines into customers + policies."""

    statement_rows: int
    customers_created: int
    policies_created: int
    policies_skipped: int


class StatementCsvUploadOut(BaseModel):
    """Result of uploading a statement CSV into statement_policy_lines."""

    rows_inserted: int
    source_file: str
    replace_existing: bool
    materialize: Optional[StatementImportStats] = None


STATEMENT_CSV_MAX_BYTES = 15 * 1024 * 1024

# Manual policy form slugs → insurance_types.insurance_type_name
POLICY_SLUG_TO_TYPE_NAME = {
    "auto": "Private Car",
    "health": "Health",
    "home": "Property",
    "business": "Property",
    "life": "Health",
}


async def _resolve_insurance_type_id(db, slug: str) -> int:
    name = POLICY_SLUG_TO_TYPE_NAME.get((slug or "auto").lower(), "Private Car")
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


async def _default_payment_status_id(db) -> Optional[int]:
    async with db.execute(
        "SELECT payment_status_id FROM payment_statuses WHERE status_name = 'Unknown' LIMIT 1"
    ) as cur:
        row = await cur.fetchone()
    return int(row[0]) if row else None


async def _insert_empty_policy_detail(db, policy_id: int, insurance_type_id: int) -> None:
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


def _policy_row_to_model(row: dict) -> Policy:
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


def _customer_row_to_model(row: dict) -> Customer:
    return Customer(
        id=str(row["id"]),
        user_id=row["user_id"],
        name=row["name"] or "",
        email=row.get("email"),
        phone=row.get("phone"),
        address=row.get("address"),
        created_at=row["created_at"] or "",
    )


class StatementPolicyLineOut(BaseModel):
    """One row from imported statement CSV (staging table)."""

    id: int
    customer_name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    vehicle_registration: Optional[str] = None
    vehicle_details: Optional[str] = None
    insurer_company: Optional[str] = None
    policy_number: Optional[str] = None
    premium_total: Optional[str] = None
    payment_status: Optional[str] = None
    date_of_issue: Optional[str] = None
    policy_end_date: Optional[str] = None
    source_file: str
    imported_at: str


class RenewalHistory(BaseModel):
    id: str
    policy_id: str
    renewal_date: str
    amount: float
    status: str
    created_at: str

class RenewalHistoryCreate(BaseModel):
    policy_id: str
    renewal_date: str
    amount: float
    status: str = "completed"


# ============= DEFAULT USER (no login) =============

DEFAULT_USER_ID = "user_dev_local"
DEFAULT_USER_EMAIL = "dev@local.insurance"


async def get_default_user() -> User:
    """Single-tenant app: all data is scoped to one default user row."""
    db = await get_db()
    try:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (DEFAULT_USER_ID,)) as cursor:
            row = await cursor.fetchone()
        if row:
            return User(**dict(row))
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """INSERT INTO users (user_id, email, name, picture, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (DEFAULT_USER_ID, DEFAULT_USER_EMAIL, "Default User", None, now),
        )
        await db.commit()
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (DEFAULT_USER_ID,)) as cursor:
            row = await cursor.fetchone()
        return User(**dict(row))
    finally:
        await db.close()


# ============= CUSTOMER ENDPOINTS =============

def _parse_customer_id(customer_id: str) -> int:
    try:
        return int(customer_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Customer not found")


def _parse_policy_id(policy_id: str) -> int:
    try:
        return int(policy_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Policy not found")


def _is_pending_payment_label(name: Optional[str]) -> bool:
    return (name or "").strip().upper() == PENDING_PAYMENT_STATUS_NAME


async def _payment_status_id_by_name(db, name: str) -> Optional[int]:
    async with db.execute(
        "SELECT payment_status_id FROM payment_statuses WHERE status_name = ?",
        (name,),
    ) as c:
        row = await c.fetchone()
    return int(row[0]) if row else None


_CUSTOMER_SELECT = """
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


_POLICY_SELECT = """
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


@api_router.get("/customers", response_model=List[Customer])
async def get_customers():
    """Get all customers for current user"""
    user = await get_default_user()

    db = await get_db()
    try:
        async with db.execute(
            f"{_CUSTOMER_SELECT} WHERE c.user_id = ? ORDER BY c.created_at DESC",
            (user.user_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        return [_customer_row_to_model(dict(row)) for row in rows]
    finally:
        await db.close()


@api_router.post("/customers", response_model=Customer)
async def create_customer(customer: CustomerCreate):
    """Create a new customer"""
    user = await get_default_user()

    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO customers (user_id, full_name, email, phone_number, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                user.user_id,
                customer.name,
                customer.email,
                customer.phone,
                now,
                now,
            ),
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
            f"{_CUSTOMER_SELECT} WHERE c.customer_id = ?",
            (cid,),
        ) as cursor:
            row = await cursor.fetchone()

        return _customer_row_to_model(dict(row))
    finally:
        await db.close()


@api_router.get("/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str):
    """Get a specific customer"""
    user = await get_default_user()
    cid = _parse_customer_id(customer_id)

    db = await get_db()
    try:
        async with db.execute(
            f"{_CUSTOMER_SELECT} WHERE c.customer_id = ? AND c.user_id = ?",
            (cid, user.user_id),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Customer not found")

        return _customer_row_to_model(dict(row))
    finally:
        await db.close()


@api_router.put("/customers/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, customer: CustomerCreate):
    """Update a customer"""
    user = await get_default_user()
    cid = _parse_customer_id(customer_id)

    db = await get_db()
    try:
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
            (
                customer.name,
                customer.email,
                customer.phone,
                now,
                cid,
                user.user_id,
            ),
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
            f"{_CUSTOMER_SELECT} WHERE c.customer_id = ?",
            (cid,),
        ) as cursor:
            row = await cursor.fetchone()

        return _customer_row_to_model(dict(row))
    finally:
        await db.close()


@api_router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str):
    """Delete a customer"""
    user = await get_default_user()
    cid = _parse_customer_id(customer_id)

    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM customers WHERE customer_id = ? AND user_id = ?",
            (cid, user.user_id),
        )
        await db.commit()

        return {"message": "Customer deleted successfully"}
    finally:
        await db.close()


# ============= POLICY ENDPOINTS =============

@api_router.get("/policies", response_model=List[Policy])
async def get_policies():
    """Get all policies for current user"""
    user = await get_default_user()

    db = await get_db()
    try:
        async with db.execute(
            f"{_POLICY_SELECT} WHERE cu.user_id = ? ORDER BY p.created_at DESC",
            (user.user_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        return [_policy_row_to_model(dict(row)) for row in rows]
    finally:
        await db.close()


_EXPORT_POLICY_SELECT = """
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


def _parse_date_flexible_for_export(val) -> Optional[date]:
    """Normalize ISO, dd-mm-yyyy, or datetime strings to a calendar date."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    if "T" in s or (len(s) > 10 and s[10] == " "):
        try:
            if "T" in s:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(s[:19].replace(" ", "T", 1))
            return dt.date()
        except ValueError:
            pass
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            pass
    m = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None


def _export_row_in_month(row: dict, by: str, year: int, month: int) -> bool:
    if by == "policy_end_date":
        key = "end_date"
    elif by == "date_of_issue":
        key = "start_date"
    else:
        return False
    d = _parse_date_flexible_for_export(row.get(key))
    if d is None:
        return False
    return d.year == year and d.month == month


EXPORT_POLICIES_BY_SLUG = {
    "date_of_issue": "month-of-issue",
    "policy_end_date": "expiring",
}


def _csv_string_to_utf8_bom_bytes(text: str) -> bytes:
    return ("\ufeff" + text).encode("utf-8")


CUSTOMERS_FULL_CSV_HEADERS = [
    "customer_id",
    "user_id",
    "full_name",
    "email",
    "phone_number",
    "created_at",
    "updated_at",
]

CUSTOMER_ADDRESSES_CSV_HEADERS = [
    "address_id",
    "customer_id",
    "address_line1",
    "address_line2",
    "area",
    "city",
    "district",
    "state",
    "postal_code",
    "country",
    "raw_address",
    "created_at",
    "updated_at",
]

RENEWAL_HISTORY_CSV_HEADERS = [
    "id",
    "policy_id",
    "renewal_date",
    "amount",
    "status",
    "created_at",
]


async def _export_statement_policy_lines_csv(db) -> str:
    """All columns present on statement_policy_lines (handles legacy migrations)."""
    async with db.execute("PRAGMA table_info(statement_policy_lines)") as cur:
        cols = [r[1] for r in await cur.fetchall()]
    if not cols:
        buf = io.StringIO()
        csv.writer(buf).writerow(["(no statement_policy_lines table)"])
        return buf.getvalue()
    col_list = ", ".join(cols)
    async with db.execute(
        f"SELECT {col_list} FROM statement_policy_lines ORDER BY id"
    ) as cur:
        rows = await cur.fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(cols)
    for row in rows:
        d = dict(row)
        writer.writerow([d.get(c) for c in cols])
    return buf.getvalue()


async def _build_full_data_zip_bytes(db, user_id: str) -> bytes:
    zip_buf = io.BytesIO()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # --- customers ---
        async with db.execute(
            """SELECT customer_id, user_id, full_name, email, phone_number, created_at, updated_at
               FROM customers WHERE user_id = ? ORDER BY customer_id""",
            (user_id,),
        ) as cur:
            crows = [dict(r) for r in await cur.fetchall()]
        cbuf = io.StringIO()
        cw = csv.writer(cbuf)
        cw.writerow(CUSTOMERS_FULL_CSV_HEADERS)
        for r in crows:
            cw.writerow([r.get(h) for h in CUSTOMERS_FULL_CSV_HEADERS])
        zf.writestr("customers.csv", _csv_string_to_utf8_bom_bytes(cbuf.getvalue()))

        # --- customer_addresses (all columns) ---
        async with db.execute(
            """SELECT a.address_id, a.customer_id, a.address_line1, a.address_line2, a.area, a.city,
                      a.district, a.state, a.postal_code, a.country, a.raw_address, a.created_at, a.updated_at
               FROM customer_addresses a
               INNER JOIN customers c ON a.customer_id = c.customer_id
               WHERE c.user_id = ?
               ORDER BY a.customer_id, a.address_id""",
            (user_id,),
        ) as cur:
            arows = [dict(r) for r in await cur.fetchall()]
        abuf = io.StringIO()
        aw = csv.writer(abuf)
        aw.writerow(CUSTOMER_ADDRESSES_CSV_HEADERS)
        for r in arows:
            aw.writerow([r.get(h) for h in CUSTOMER_ADDRESSES_CSV_HEADERS])
        zf.writestr("customer_addresses.csv", _csv_string_to_utf8_bom_bytes(abuf.getvalue()))

        # --- policies (wide join, all rows for user) ---
        async with db.execute(
            f"{_EXPORT_POLICY_SELECT} WHERE c.user_id = ? "
            "ORDER BY p.policy_end_date IS NULL, p.policy_end_date ASC, p.policy_id ASC",
            (user_id,),
        ) as cur:
            prows = [dict(r) for r in await cur.fetchall()]
        pbuf = io.StringIO()
        pw = csv.writer(pbuf)
        pw.writerow(EXPORT_POLICIES_CSV_HEADERS)
        export_results = []
        export_pids = []
        for r in prows:
            d = dict(r)
            er = build_export_row(d)
            export_results.append(er)
            export_pids.append(d.get("policy_id"))
            pw.writerow(er.cells)
        validate_and_summarize_export(export_results, export_pids)
        zf.writestr("policies.csv", _csv_string_to_utf8_bom_bytes(pbuf.getvalue()))

        for split_name, bucket in (
            ("motor_export.csv", "motor"),
            ("health_export.csv", "health"),
            ("non_motor_export.csv", "non_motor"),
        ):
            sbuf = io.StringIO()
            sw = csv.writer(sbuf)
            sw.writerow(EXPORT_POLICIES_CSV_HEADERS)
            for row_cells in render_split_csv_rows(export_results, bucket):
                sw.writerow(row_cells)
            zf.writestr(split_name, _csv_string_to_utf8_bom_bytes(sbuf.getvalue()))

        # --- renewal_history ---
        async with db.execute(
            """SELECT rh.id, rh.policy_id, rh.renewal_date, rh.amount, rh.status, rh.created_at
               FROM renewal_history rh
               INNER JOIN policies p ON rh.policy_id = p.policy_id
               INNER JOIN customers c ON p.customer_id = c.customer_id
               WHERE c.user_id = ?
               ORDER BY rh.renewal_date, rh.id""",
            (user_id,),
        ) as cur:
            rhrows = [dict(r) for r in await cur.fetchall()]
        rhbuf = io.StringIO()
        rhw = csv.writer(rhbuf)
        rhw.writerow(RENEWAL_HISTORY_CSV_HEADERS)
        for r in rhrows:
            rhw.writerow([r.get(h) for h in RENEWAL_HISTORY_CSV_HEADERS])
        zf.writestr("renewal_history.csv", _csv_string_to_utf8_bom_bytes(rhbuf.getvalue()))

        # --- statement CSV staging (full table, all columns) ---
        stmt_csv = await _export_statement_policy_lines_csv(db)
        zf.writestr("statement_policy_lines.csv", _csv_string_to_utf8_bom_bytes(stmt_csv))

        readme = (
            "Insurance data export\n"
            f"Generated (UTC): {stamp}\n"
            "Files:\n"
            "- customers.csv — customer records for your account\n"
            "- customer_addresses.csv — address rows linked to those customers\n"
            "- policies.csv — UTF-8 BOM; slim columns (customer, policy, category, primary_details, …) plus extra_details JSON (full motor/health/property + policy_extras)\n"
            "- motor_export.csv / health_export.csv / non_motor_export.csv — same layout as policies.csv, filtered by category\n"
            "- renewal_history.csv — renewal rows for your policies\n"
            "- statement_policy_lines.csv — raw imported statement CSV staging (all DB columns)\n"
        )
        zf.writestr("README.txt", readme.encode("utf-8"))

    zip_buf.seek(0)
    return zip_buf.getvalue()


@api_router.get("/export/policies-csv")
async def export_policies_csv(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    by: str = Query(
        "policy_end_date",
        description="Month filter: policy_end_date (expiring in that month) or date_of_issue (issued that month)",
    ),
):
    """
    Download policies for the current user as CSV, filtered to rows whose chosen date falls
    in the given calendar month (local date extracted from stored values).
    """
    allowed = {"policy_end_date", "date_of_issue"}
    if by not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid 'by' (use one of: {', '.join(sorted(allowed))})",
        )

    user = await get_default_user()
    db = await get_db()
    try:
        async with db.execute(
            f"{_EXPORT_POLICY_SELECT} WHERE c.user_id = ? "
            "ORDER BY p.policy_end_date IS NULL, p.policy_end_date ASC, p.policy_id ASC",
            (user.user_id,),
        ) as cursor:
            rows = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()

    filtered = [r for r in rows if _export_row_in_month(r, by, year, month)]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_POLICIES_CSV_HEADERS)
    export_results = []
    export_pids = []
    for r in filtered:
        d = dict(r)
        er = build_export_row(d)
        export_results.append(er)
        export_pids.append(d.get("policy_id"))
        writer.writerow(er.cells)
    validate_and_summarize_export(export_results, export_pids)

    by_slug = EXPORT_POLICIES_BY_SLUG.get(by, by.replace("_", "-"))
    filename = f"policies_{year:04d}-{month:02d}_by-{by_slug}.csv"
    body = ("\ufeff" + buf.getvalue()).encode("utf-8")
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@api_router.get("/export/full-data-zip")
async def export_full_data_zip():
    """
    ZIP containing CSV exports: customers, customer_addresses, policies (slim columns + JSON extra_details),
    category split CSVs (motor / health / non-motor), renewal_history, and statement_policy_lines.
    """
    user = await get_default_user()
    db = await get_db()
    try:
        data = await _build_full_data_zip_bytes(db, user.user_id)
    finally:
        await db.close()
    fn = f"insurance_full_export_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@api_router.post("/policies", response_model=Policy)
async def create_policy(policy: PolicyCreate):
    """Create a new policy"""
    user = await get_default_user()

    try:
        cust_pk = int(policy.customer_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Customer not found")

    created_at = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
        async with db.execute(
            "SELECT customer_id FROM customers WHERE customer_id = ? AND user_id = ?",
            (cust_pk, user.user_id),
        ) as cursor:
            customer = await cursor.fetchone()

        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        it_id = await _resolve_insurance_type_id(db, policy.policy_type)
        pay_id = await _default_payment_status_id(db)

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

        await _insert_empty_policy_detail(db, new_pid, it_id)
        await db.commit()

        async with db.execute(
            f"{_POLICY_SELECT} WHERE p.policy_id = ?",
            (new_pid,),
        ) as cursor:
            row = await cursor.fetchone()

        return _policy_row_to_model(dict(row))
    finally:
        await db.close()


@api_router.get("/policies/{policy_id}", response_model=Policy)
async def get_policy(policy_id: str):
    """Get a specific policy"""
    user = await get_default_user()
    pid = _parse_policy_id(policy_id)

    db = await get_db()
    try:
        async with db.execute(
            f"{_POLICY_SELECT} WHERE p.policy_id = ? AND cu.user_id = ?",
            (pid, user.user_id),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Policy not found")

        return _policy_row_to_model(dict(row))
    finally:
        await db.close()


def _sql_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@api_router.get("/policies/{policy_id}/detail", response_model=PolicyDetailBundle)
async def get_policy_detail_bundle(policy_id: str):
    """Read-only: policy, customer, category group, and motor/health/property rows when present."""
    user = await get_default_user()
    pid = _parse_policy_id(policy_id)

    db = await get_db()
    try:
        async with db.execute(
            f"{_POLICY_SELECT} WHERE p.policy_id = ? AND cu.user_id = ?",
            (pid, user.user_id),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Policy not found")

        policy = _policy_row_to_model(dict(row))
        cid = int(row["customer_id"])

        async with db.execute(
            f"{_CUSTOMER_SELECT} WHERE c.customer_id = ? AND c.user_id = ?",
            (cid, user.user_id),
        ) as cur:
            crow = await cur.fetchone()
        if not crow:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer = _customer_row_to_model(dict(crow))

        async with db.execute(
            """SELECT it.category_group FROM policies p
               JOIN insurance_types it ON p.insurance_type_id = it.insurance_type_id
               WHERE p.policy_id = ?""",
            (pid,),
        ) as cur:
            cg_row = await cur.fetchone()
        category_group = (cg_row[0] if cg_row else "Motor") or "Motor"

        motor = None
        async with db.execute(
            """SELECT vehicle_no, vehicle_details, idv_of_vehicle, engine_no, chassis_no,
                      od_premium, tp_premium
               FROM motor_policy_details WHERE policy_id = ?""",
            (pid,),
        ) as cur:
            m = await cur.fetchone()
        if m:
            md = dict(m)
            motor = MotorPolicyDetailsDto(
                vehicle_no=md.get("vehicle_no"),
                vehicle_details=md.get("vehicle_details"),
                idv_of_vehicle=_sql_float(md.get("idv_of_vehicle")),
                engine_no=md.get("engine_no"),
                chassis_no=md.get("chassis_no"),
                od_premium=_sql_float(md.get("od_premium")),
                tp_premium=_sql_float(md.get("tp_premium")),
            )

        health = None
        async with db.execute(
            """SELECT plan_name, sum_insured, cover_type, members_covered,
                      base_premium, additional_premium
               FROM health_policy_details WHERE policy_id = ?""",
            (pid,),
        ) as cur:
            h = await cur.fetchone()
        if h:
            hd = dict(h)
            health = HealthPolicyDetailsDto(
                plan_name=hd.get("plan_name"),
                sum_insured=_sql_float(hd.get("sum_insured")),
                cover_type=hd.get("cover_type"),
                members_covered=hd.get("members_covered"),
                base_premium=_sql_float(hd.get("base_premium")),
                additional_premium=_sql_float(hd.get("additional_premium")),
            )

        property_detail = None
        async with db.execute(
            """SELECT product_name, sum_insured, sub_product, risk_location,
                      base_premium, additional_premium
               FROM property_policy_details WHERE policy_id = ?""",
            (pid,),
        ) as cur:
            pr = await cur.fetchone()
        if pr:
            pd = dict(pr)
            property_detail = PropertyPolicyDetailsDto(
                product_name=pd.get("product_name"),
                sum_insured=_sql_float(pd.get("sum_insured")),
                sub_product=pd.get("sub_product"),
                risk_location=pd.get("risk_location"),
                base_premium=_sql_float(pd.get("base_premium")),
                additional_premium=_sql_float(pd.get("additional_premium")),
            )

        return PolicyDetailBundle(
            policy=policy,
            customer=customer,
            category_group=category_group,
            motor=motor,
            health=health,
            property_detail=property_detail,
        )
    finally:
        await db.close()


@api_router.put("/policies/{policy_id}", response_model=Policy)
async def update_policy(policy_id: str, policy: PolicyCreate):
    """Update a policy"""
    user = await get_default_user()
    pid = _parse_policy_id(policy_id)

    db = await get_db()
    try:
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

        it_id = await _resolve_insurance_type_id(db, policy.policy_type)
        pay_id = await _default_payment_status_id(db)
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
            f"{_POLICY_SELECT} WHERE p.policy_id = ?",
            (pid,),
        ) as cursor:
            row = await cursor.fetchone()

        return _policy_row_to_model(dict(row))
    finally:
        await db.close()


@api_router.patch("/policies/{policy_id}/contact", response_model=Policy)
async def patch_policy_contact(
    policy_id: str,
    body: PolicyContactUpdate,
):
    """Update renewal contact fields only (last_contacted_at, contact_status, follow_up_date)."""
    user = await get_default_user()
    pid = _parse_policy_id(policy_id)

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "contact_status" in patch and patch["contact_status"] is not None:
        if patch["contact_status"] not in ALLOWED_POLICY_CONTACT_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"contact_status must be one of: {sorted(ALLOWED_POLICY_CONTACT_STATUSES)}",
            )

    db = await get_db()
    try:
        async with db.execute(
            f"""SELECT p.policy_id FROM policies p
                JOIN customers cu ON p.customer_id = cu.customer_id
                WHERE p.policy_id = ? AND cu.user_id = ?""",
            (pid, user.user_id),
        ) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=404, detail="Policy not found")

        sets = []
        params = []
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
            f"{_POLICY_SELECT} WHERE p.policy_id = ?",
            (pid,),
        ) as cursor:
            row = await cursor.fetchone()

        return _policy_row_to_model(dict(row))
    finally:
        await db.close()


@api_router.patch("/policies/{policy_id}/payment", response_model=Policy)
async def patch_policy_payment(
    policy_id: str,
    body: PolicyPaymentUpdate,
):
    """Update payment status when current status is PENDING (e.g. mark paid channel)."""
    user = await get_default_user()
    pid = _parse_policy_id(policy_id)

    new_label = (body.payment_status or "").strip()
    if new_label not in ALLOWED_PAYMENT_UPDATE_FROM_PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"payment_status must be one of: {sorted(ALLOWED_PAYMENT_UPDATE_FROM_PENDING)}",
        )

    note = (body.payment_note or "").strip() or None
    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
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
        if not _is_pending_payment_label(current):
            raise HTTPException(
                status_code=400,
                detail="Payment can only be updated from PENDING in this workflow.",
            )

        new_id = await _payment_status_id_by_name(db, new_label)
        if new_id is None:
            await db.execute(
                "INSERT INTO payment_statuses (status_name) VALUES (?)",
                (new_label,),
            )
            new_id = await _payment_status_id_by_name(db, new_label)

        await db.execute(
            """UPDATE policies SET payment_status_id = ?, payment_note = ?,
                   payment_updated_at = ?, updated_at = ?
               WHERE policy_id = ?""",
            (new_id, note, now, now, pid),
        )
        await db.commit()

        async with db.execute(
            f"{_POLICY_SELECT} WHERE p.policy_id = ?",
            (pid,),
        ) as cursor:
            out = await cursor.fetchone()

        return _policy_row_to_model(dict(out))
    finally:
        await db.close()


@api_router.patch("/policies/{policy_id}/renewal-resolution", response_model=Policy)
async def patch_policy_renewal_resolution(
    policy_id: str,
    body: PolicyRenewalResolutionUpdate,
):
    """Set renewal resolution for expired / missed-opportunity workflow. Records stay in DB."""
    user = await get_default_user()
    pid = _parse_policy_id(policy_id)

    if body.renewal_status not in ALLOWED_RENEWAL_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"renewal_status must be one of: {sorted(ALLOWED_RENEWAL_STATUSES)}",
        )

    note = (body.renewal_resolution_note or "").strip() or None
    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
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
            f"{_POLICY_SELECT} WHERE p.policy_id = ?",
            (pid,),
        ) as cursor:
            row = await cursor.fetchone()

        return _policy_row_to_model(dict(row))
    finally:
        await db.close()


@api_router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: str):
    """Delete a policy"""
    user = await get_default_user()
    pid = _parse_policy_id(policy_id)

    db = await get_db()
    try:
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
    finally:
        await db.close()


@api_router.post("/import/statement-csv", response_model=StatementCsvUploadOut)
async def upload_statement_csv(
    file: UploadFile = File(...),
    replace_existing: bool = Form(True),
    promote_to_dashboard: bool = Form(False),
):
    """
    Upload a statement CSV (same format as ``import_march_statements.py``) into
    ``statement_policy_lines``. Optionally replace prior rows for the same filename, then
    optionally run the same materialize step as POST /import/statement-lines.
    """
    user = await get_default_user()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    safe_name = Path(file.filename).name
    if not safe_name.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Expected a .csv file (export from Excel as CSV, not .xlsx).",
        )
    data = await file.read()
    if len(data) > STATEMENT_CSV_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {STATEMENT_CSV_MAX_BYTES // (1024 * 1024)} MB).",
        )
    try:
        n = import_csv_from_bytes(
            data, safe_name, replace_source=replace_existing
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=400, detail="Could not decode file as UTF-8 text."
        ) from e

    materialize_out: Optional[StatementImportStats] = None
    if promote_to_dashboard:
        db = await get_db()
        try:
            stats = await materialize_statement_lines(db, user.user_id)
            await db.commit()
            materialize_out = StatementImportStats(**stats)
        finally:
            await db.close()

    return StatementCsvUploadOut(
        rows_inserted=n,
        source_file=safe_name,
        replace_existing=replace_existing,
        materialize=materialize_out,
    )


@api_router.get("/import/statement-lines/summary")
async def statement_import_summary():
    """How many rows are in statement_policy_lines (from CSV import scripts)."""
    await get_default_user()
    db = await get_db()
    try:
        async with db.execute("SELECT COUNT(*) FROM statement_policy_lines") as cur:
            n = (await cur.fetchone())[0]
        return {"statement_rows": n}
    finally:
        await db.close()


@api_router.get("/statement-lines", response_model=List[StatementPolicyLineOut])
async def list_statement_lines():
    """Browse imported CSV rows: first column split into customer name + address."""
    await get_default_user()
    db = await get_db()
    try:
        async with db.execute(
            """
            SELECT * FROM statement_policy_lines
            ORDER BY id DESC
            LIMIT 5000
            """
        ) as cur:
            rows = await cur.fetchall()
        out: List[StatementPolicyLineOut] = []
        for row in rows:
            d = dict(row)
            cn = (d.get("customer_name") or "").strip()
            addr = d.get("address")
            if addr is not None and str(addr).strip() == "":
                addr = None
            elif addr is not None:
                addr = str(addr).strip()
            if not cn and d.get("name_and_address"):
                cn, addr = split_name_address(d.get("name_and_address"))
            if not cn:
                cn = "Unknown"
            out.append(
                StatementPolicyLineOut(
                    id=d["id"],
                    customer_name=cn[:200],
                    address=addr,
                    phone_number=d.get("phone_number"),
                    vehicle_registration=d.get("vehicle_registration"),
                    vehicle_details=d.get("vehicle_details"),
                    insurer_company=d.get("insurer_company"),
                    policy_number=d.get("policy_number"),
                    premium_total=d.get("premium_total"),
                    payment_status=d.get("payment_status"),
                    date_of_issue=d.get("date_of_issue"),
                    policy_end_date=d.get("policy_end_date"),
                    source_file=d["source_file"],
                    imported_at=d["imported_at"],
                )
            )
        return out
    finally:
        await db.close()


@api_router.post("/import/statement-lines", response_model=StatementImportStats)
async def statement_import_run():
    """
    Create customers and policies for the current user from statement_policy_lines.
    Safe to run more than once: skips rows whose policy_number already exists.
    """
    user = await get_default_user()
    db = await get_db()
    try:
        stats = await materialize_statement_lines(db, user.user_id)
        await db.commit()
        return StatementImportStats(**stats)
    finally:
        await db.close()


# ============= RENEWAL REMINDERS =============


def _parse_policy_end_date(val) -> date:
    """DB stores ISO date or datetime string; normalize to date."""
    s = str(val).strip()
    if "T" in s:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    return datetime.fromisoformat(s[:10]).date()


@api_router.get("/renewals/reminders")
async def get_renewal_reminders():
    """
    Renewal buckets for active policies. Uses the server's **local calendar date** for
    ``today`` (policy end dates are calendar dates from imports).

    Summary (cumulative — active policies with end_date within next N days):
    - ``expiring_within_7_days``, ``expiring_within_15_days``, ``expiring_within_30_days`` for the
      renewal reminders list.
    - ``expiring_within_365_days`` for the dashboard "Expiring soon (≤12 months)" metric card.
    """
    user = await get_default_user()

    today = date.today()
    day_1 = today + timedelta(days=1)
    day_7 = today + timedelta(days=7)
    day_15 = today + timedelta(days=15)
    day_30 = today + timedelta(days=30)
    day_90 = today + timedelta(days=90)
    day_365 = today + timedelta(days=365)

    db = await get_db()
    try:
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
            end_date = _parse_policy_end_date(policy_dict["end_date"])

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
    finally:
        await db.close()


def _expiring_list_window_bounds(window: str, today: date) -> tuple[date, date]:
    """
    Inclusive [min_end, max_end] for policy_end_date, matching dashboard summary counts:
    - today: end == today
    - 7/15/30: today <= end <= today+N (same as expiring_within_*_days in /renewals/reminders).
    """
    day_7 = today + timedelta(days=7)
    day_15 = today + timedelta(days=15)
    day_30 = today + timedelta(days=30)
    if window == "today":
        return today, today
    if window == "7":
        return today, day_7
    if window == "15":
        return today, day_15
    if window == "30":
        return today, day_30
    raise ValueError(f"invalid window: {window}")


@api_router.get("/renewals/expiring-list")
async def get_expiring_policies_list(
    window: str = Query(
        ...,
        description="today | 7 | 15 | 30 | expired — same rules as dashboard renewal summary",
        pattern="^(today|7|15|30|expired)$",
    ),
):
    """
    Active policies whose end date falls in the same window as the dashboard renewal row counts.
    For ``expired``: active policies with policy_end_date before today (matches summary ``expired``).
    Non-expired windows: sorted by policy_end_date ascending. Expired: descending (most recent first).
    """
    user = await get_default_user()
    today = date.today()

    db = await get_db()
    try:
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
            end_d = _parse_policy_end_date(d["end_date"])
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
    finally:
        await db.close()


async def _load_user_snapshot_payload(user_id: str) -> dict:
    db = await get_db()
    try:
        snapshot = {
            "version": datetime.now(timezone.utc).isoformat(),
            "schema": "normalized_v2",
            "user_id": user_id,
            "customers": [],
            "policies": [],
            "renewal_history": [],
        }
        async with db.execute(
            f"{_CUSTOMER_SELECT} WHERE c.user_id = ?",
            (user_id,),
        ) as cursor:
            for row in await cursor.fetchall():
                snapshot["customers"].append(
                    _customer_row_to_model(dict(row)).model_dump()
                )
        async with db.execute(
            f"{_POLICY_SELECT} WHERE cu.user_id = ?",
            (user_id,),
        ) as cursor:
            for row in await cursor.fetchall():
                snapshot["policies"].append(
                    _policy_row_to_model(dict(row)).model_dump()
                )
        async with db.execute(
            """SELECT rh.* FROM renewal_history rh
               JOIN policies p ON rh.policy_id = p.policy_id
               JOIN customers c ON p.customer_id = c.customer_id
               WHERE c.user_id = ?""",
            (user_id,),
        ) as cursor:
            snapshot["renewal_history"] = [dict(row) for row in await cursor.fetchall()]
        return snapshot
    finally:
        await db.close()


# ============= SYNC ENDPOINTS =============
# sync_info may contain historical rows from earlier app versions; there is no cloud storage backend.

@api_router.post("/sync/generate-snapshot")
async def generate_snapshot():
    """Build JSON snapshot (Customer, Policy, RenewalHistory) for offline/import."""
    user = await get_default_user()
    return await _load_user_snapshot_payload(user.user_id)


@api_router.get("/sync/status")
async def get_sync_status():
    """Latest sync_info row for the user."""
    user = await get_default_user()

    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM sync_info WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user.user_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return {"last_sync": None, "status": "never_synced"}

        return dict(row)
    finally:
        await db.close()


@api_router.get("/statistics/dashboard")
async def statistics_dashboard():
    """Payment, renewal, expiry, and customer metrics (current month + trends)."""
    user = await get_default_user()
    return await build_dashboard_statistics(user.user_id)


# ============= ROOT & HEALTH =============

@api_router.get("/")
async def root():
    return {"message": "Insurance App API", "version": "1.0.0"}

@api_router.get("/health")
async def health():
    """Liveness + SQLite row counts (verify the API uses the DB file you expect)."""
    out: dict = {
        "status": "healthy",
        "database_path": str(DB_PATH.resolve()),
        "database_exists": DB_PATH.is_file(),
    }
    if not out["database_exists"]:
        out["hint"] = (
            "No insurance.db yet. Run the API from backend/ (see run_backend.sh) so the file is "
            "created next to server.py, or set INSURANCE_DB_PATH in backend/.env to an absolute path."
        )
        return out
    try:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            for table in ("users", "customers", "policies", "statement_policy_lines"):
                try:
                    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    out[f"count_{table}"] = n
                except sqlite3.OperationalError:
                    out[f"count_{table}"] = None
        finally:
            conn.close()
    except OSError as e:
        out["database_error"] = str(e)
    return out


# Include the router in the main app
app.include_router(api_router)

# CORS: explicit origins in .env (use "*" only if you accept allow_credentials=False).
_cors_raw = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
).strip()
if _cors_raw == "*":
    _cors_origins = ["*"]
    _cors_credentials = False
else:
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
    _cors_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_credentials=_cors_credentials,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("Application started")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutdown")
