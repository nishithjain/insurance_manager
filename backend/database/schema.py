"""
Canonical SQLite schema (multi-tenant via ``customers.user_id``).

Pure constant module: importing it has zero side effects, so it can be
re-used by tests, scripts, or alternative bootstrapping flows without
spinning up a real connection.
"""

from __future__ import annotations

SCHEMA_SQL: str = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    picture TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    phone_number TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customer_addresses (
    address_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    address_line1 TEXT,
    address_line2 TEXT,
    area TEXT,
    city TEXT,
    district TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT DEFAULT 'India',
    raw_address TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS agents (
    agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL UNIQUE,
    phone_number TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS insurance_types (
    insurance_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    insurance_type_name TEXT NOT NULL UNIQUE,
    category_group TEXT NOT NULL
);

-- New (post-refactor) taxonomy. Sits side-by-side with the legacy
-- ``insurance_types`` table to keep existing FKs and exports working:
--   insurance_categories  = high-level "Insurance Type"  (Motor, Health, ...)
--   policy_types          = specific variant under a category
--                           (Comprehensive, Third Party, Family Floater, ...)
-- ``policies.policy_type_id`` is added below via ALTER (see _migrate_insurance_taxonomy).
CREATE TABLE IF NOT EXISTS insurance_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS policy_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insurance_category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (insurance_category_id, name),
    FOREIGN KEY (insurance_category_id)
        REFERENCES insurance_categories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_policy_types_category
    ON policy_types(insurance_category_id);

CREATE TABLE IF NOT EXISTS payment_statuses (
    payment_status_id INTEGER PRIMARY KEY AUTOINCREMENT,
    status_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS policies (
    policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_record_id TEXT NOT NULL UNIQUE,
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
    status TEXT NOT NULL DEFAULT 'active',
    last_contacted_at TEXT,
    contact_status TEXT NOT NULL DEFAULT 'Not Contacted',
    follow_up_date TEXT,
    renewal_status TEXT NOT NULL DEFAULT 'Open',
    renewal_resolution_note TEXT,
    renewal_resolved_at TEXT,
    renewal_resolved_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (address_id) REFERENCES customer_addresses(address_id),
    FOREIGN KEY (insurance_type_id) REFERENCES insurance_types(insurance_type_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (payment_status_id) REFERENCES payment_statuses(payment_status_id)
);

CREATE TABLE IF NOT EXISTS motor_policy_details (
    policy_id INTEGER PRIMARY KEY,
    vehicle_no TEXT,
    vehicle_details TEXT,
    idv_of_vehicle NUMERIC,
    engine_no TEXT,
    chassis_no TEXT,
    od_premium NUMERIC,
    tp_premium NUMERIC,
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS health_policy_details (
    policy_id INTEGER PRIMARY KEY,
    plan_name TEXT,
    sum_insured NUMERIC,
    cover_type TEXT,
    members_covered TEXT,
    base_premium NUMERIC,
    additional_premium NUMERIC,
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS property_policy_details (
    policy_id INTEGER PRIMARY KEY,
    product_name TEXT,
    sum_insured NUMERIC,
    sub_product TEXT,
    risk_location TEXT,
    base_premium NUMERIC,
    additional_premium NUMERIC,
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS renewal_history (
    id TEXT PRIMARY KEY,
    policy_id INTEGER NOT NULL,
    renewal_date TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    last_sync_time TEXT,
    sync_status TEXT,
    file_version TEXT,
    drive_file_id TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS drive_credentials (
    user_id TEXT PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_uri TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_secret TEXT NOT NULL,
    scopes TEXT NOT NULL,
    expiry TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS statement_policy_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    address TEXT,
    phone_number TEXT,
    vehicle_registration TEXT,
    vehicle_details TEXT,
    insurer_company TEXT,
    ncb_or_discount TEXT,
    agent TEXT,
    idv TEXT,
    engine_no TEXT,
    chassis_no TEXT,
    od_premium TEXT,
    tp_premium TEXT,
    premium_total TEXT,
    payment_status TEXT,
    date_of_issue TEXT,
    policy_end_date TEXT,
    policy_number TEXT,
    card_details TEXT,
    source_file TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_policies_customer_id ON policies(customer_id);
CREATE INDEX IF NOT EXISTS idx_policies_policy_no ON policies(policy_no);
CREATE INDEX IF NOT EXISTS idx_policies_issue_date ON policies(date_of_issue);
CREATE INDEX IF NOT EXISTS idx_policies_end_date ON policies(policy_end_date);
CREATE INDEX IF NOT EXISTS idx_policies_insurance_type_id ON policies(insurance_type_id);
CREATE INDEX IF NOT EXISTS idx_motor_vehicle_no ON motor_policy_details(vehicle_no);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);
CREATE INDEX IF NOT EXISTS idx_customers_user ON customers(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_statement_policy_lines_source ON statement_policy_lines(source_file);
CREATE INDEX IF NOT EXISTS idx_statement_policy_lines_policy_no ON statement_policy_lines(policy_number);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Authentication identity (separate from data-owner `users` table).
-- An `app_users` row represents a human who can log in; role decides what they can do.
-- Admins manage this table; regular users never hit it directly.
CREATE TABLE IF NOT EXISTS app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by INTEGER,
    last_login_at TEXT,
    FOREIGN KEY (created_by) REFERENCES app_users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_app_users_email ON app_users(email);
CREATE INDEX IF NOT EXISTS idx_app_users_role ON app_users(role);
"""

__all__ = ["SCHEMA_SQL"]
