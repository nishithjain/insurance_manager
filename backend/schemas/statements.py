"""Pydantic schemas for the statement-CSV import flow."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


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


class StatementImportStats(BaseModel):
    """Result of promoting ``statement_policy_lines`` into ``customers`` + ``policies``."""

    statement_rows: int
    customers_created: int
    policies_created: int
    policies_skipped: int


class StatementCsvUploadOut(BaseModel):
    """Result of uploading a statement CSV into ``statement_policy_lines``."""

    rows_inserted: int
    source_file: str
    replace_existing: bool
    materialize: Optional[StatementImportStats] = None
