"""
Build a single-tenant SQLite snapshot for a given ``user_id``.

This produces a self-contained export DB containing only that user's
customers, addresses, policies, and the lookup rows referenced by them.
Today no router calls it; it remains as an offline tool / library
helper for ad-hoc exports and is kept here so it lives next to the
schema it mirrors.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

from db_path import DB_PATH


# Subset of SCHEMA_SQL covering only the tables we copy into the export file.
# Kept inline because the export DB intentionally drops constraints/FKs to
# avoid pulling in unrelated tables (sessions, sync_info, etc.).
_EXPORT_SCHEMA_SQL = """
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    phone_number TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE customer_addresses (
    address_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    address_line1 TEXT,
    address_line2 TEXT,
    area TEXT,
    city TEXT,
    district TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT,
    raw_address TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE insurance_types (
    insurance_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    insurance_type_name TEXT NOT NULL,
    category_group TEXT NOT NULL
);
CREATE TABLE companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL
);
CREATE TABLE agents (
    agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    phone_number TEXT,
    email TEXT
);
CREATE TABLE payment_statuses (
    payment_status_id INTEGER PRIMARY KEY AUTOINCREMENT,
    status_name TEXT NOT NULL
);
CREATE TABLE policies (
    policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_record_id TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    address_id INTEGER,
    insurance_type_id INTEGER NOT NULL,
    company_id INTEGER,
    agent_id INTEGER,
    ncb_discount TEXT,
    total_premium NUMERIC,
    payment_status_id INTEGER,
    date_of_issue TEXT,
    policy_end_date TEXT,
    policy_no TEXT,
    card_details TEXT,
    status TEXT NOT NULL,
    last_contacted_at TEXT,
    contact_status TEXT NOT NULL DEFAULT 'Not Contacted',
    follow_up_date TEXT,
    renewal_status TEXT NOT NULL DEFAULT 'Open',
    renewal_resolution_note TEXT,
    renewal_resolved_at TEXT,
    renewal_resolved_by TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE motor_policy_details (
    policy_id INTEGER PRIMARY KEY,
    vehicle_no TEXT,
    vehicle_details TEXT,
    idv_of_vehicle NUMERIC,
    engine_no TEXT,
    chassis_no TEXT,
    od_premium NUMERIC,
    tp_premium NUMERIC
);
CREATE TABLE health_policy_details (
    policy_id INTEGER PRIMARY KEY,
    plan_name TEXT,
    sum_insured NUMERIC,
    cover_type TEXT,
    members_covered TEXT,
    base_premium NUMERIC,
    additional_premium NUMERIC
);
CREATE TABLE property_policy_details (
    policy_id INTEGER PRIMARY KEY,
    product_name TEXT,
    sum_insured NUMERIC,
    sub_product TEXT,
    risk_location TEXT,
    base_premium NUMERIC,
    additional_premium NUMERIC
);
CREATE TABLE renewal_history (
    id TEXT PRIMARY KEY,
    policy_id INTEGER NOT NULL,
    renewal_date TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def export_user_insurance_sqlite_bytes(user_id: str) -> bytes:
    """
    Return a single-user SQLite snapshot as raw bytes.

    Caller is responsible for choosing the response/HTTP wrapping. The
    temporary file backing the snapshot is deleted before returning.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    path = tmp.name
    main = str(DB_PATH)
    try:
        exp = sqlite3.connect(path)
        try:
            exp.execute("PRAGMA foreign_keys = OFF")
            exp.executescript(_EXPORT_SCHEMA_SQL)
            exp.execute("ATTACH DATABASE ? AS m", (main,))

            exp.execute(
                "INSERT INTO customers SELECT * FROM m.customers WHERE user_id = ?",
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO customer_addresses SELECT ca.*
                FROM m.customer_addresses ca
                INNER JOIN m.customers c ON ca.customer_id = c.customer_id
                WHERE c.user_id = ?
                """,
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO insurance_types SELECT it.*
                FROM m.insurance_types it
                WHERE it.insurance_type_id IN (
                    SELECT DISTINCT p.insurance_type_id FROM m.policies p
                    INNER JOIN m.customers c ON p.customer_id = c.customer_id
                    WHERE c.user_id = ?
                )
                """,
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO companies SELECT co.*
                FROM m.companies co
                WHERE co.company_id IN (
                    SELECT DISTINCT p.company_id FROM m.policies p
                    INNER JOIN m.customers c ON p.customer_id = c.customer_id
                    WHERE c.user_id = ? AND p.company_id IS NOT NULL
                )
                """,
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO agents SELECT a.*
                FROM m.agents a
                WHERE a.agent_id IN (
                    SELECT DISTINCT p.agent_id FROM m.policies p
                    INNER JOIN m.customers c ON p.customer_id = c.customer_id
                    WHERE c.user_id = ? AND p.agent_id IS NOT NULL
                )
                """,
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO payment_statuses SELECT ps.*
                FROM m.payment_statuses ps
                WHERE ps.payment_status_id IN (
                    SELECT DISTINCT p.payment_status_id FROM m.policies p
                    INNER JOIN m.customers c ON p.customer_id = c.customer_id
                    WHERE c.user_id = ? AND p.payment_status_id IS NOT NULL
                )
                """,
                (user_id,),
            )
            exp.execute(
                """
                INSERT INTO policies SELECT p.*
                FROM m.policies p
                INNER JOIN m.customers c ON p.customer_id = c.customer_id
                WHERE c.user_id = ?
                """,
                (user_id,),
            )
            for detail in (
                "motor_policy_details",
                "health_policy_details",
                "property_policy_details",
            ):
                exp.execute(
                    f"""
                    INSERT INTO {detail} SELECT d.*
                    FROM m.{detail} d
                    INNER JOIN m.policies p ON d.policy_id = p.policy_id
                    INNER JOIN m.customers c ON p.customer_id = c.customer_id
                    WHERE c.user_id = ?
                    """,
                    (user_id,),
                )
            exp.execute(
                """
                INSERT INTO renewal_history SELECT rh.*
                FROM m.renewal_history rh
                INNER JOIN m.policies p ON rh.policy_id = p.policy_id
                INNER JOIN m.customers c ON p.customer_id = c.customer_id
                WHERE c.user_id = ?
                """,
                (user_id,),
            )
            exp.commit()
            exp.execute("DETACH DATABASE m")
        finally:
            exp.close()
        return Path(path).read_bytes()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


__all__ = ["export_user_insurance_sqlite_bytes"]
