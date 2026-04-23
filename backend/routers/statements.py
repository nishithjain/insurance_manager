"""Statement CSV upload + staging-table browse + materialize-to-dashboard endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import aiosqlite
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from deps import get_current_user, get_db
from domain.constants import STATEMENT_CSV_MAX_BYTES
from import_march_statements import import_csv_from_bytes
from schemas import (
    StatementCsvUploadOut,
    StatementImportStats,
    StatementPolicyLineOut,
    User,
)
from statement_materialize import materialize_statement_lines
from statement_parse import split_name_address

router = APIRouter(tags=["statements"])


@router.post("/import/statement-csv", response_model=StatementCsvUploadOut)
async def upload_statement_csv(
    file: UploadFile = File(...),
    replace_existing: bool = Form(True),
    promote_to_dashboard: bool = Form(False),
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Upload a statement CSV (same format as ``import_march_statements.py``) into
    ``statement_policy_lines``. Optionally replace prior rows for the same filename, then
    optionally run the same materialize step as POST /import/statement-lines.
    """
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
        n = import_csv_from_bytes(data, safe_name, replace_source=replace_existing)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=400, detail="Could not decode file as UTF-8 text."
        ) from e

    materialize_out: Optional[StatementImportStats] = None
    if promote_to_dashboard:
        stats = await materialize_statement_lines(db, user.user_id)
        await db.commit()
        materialize_out = StatementImportStats(**stats)

    return StatementCsvUploadOut(
        rows_inserted=n,
        source_file=safe_name,
        replace_existing=replace_existing,
        materialize=materialize_out,
    )


@router.get("/import/statement-lines/summary")
async def statement_import_summary(
    db: aiosqlite.Connection = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """How many rows are in statement_policy_lines (from CSV import scripts)."""
    async with db.execute("SELECT COUNT(*) FROM statement_policy_lines") as cur:
        n = (await cur.fetchone())[0]
    return {"statement_rows": n}


@router.get("/statement-lines", response_model=List[StatementPolicyLineOut])
async def list_statement_lines(
    db: aiosqlite.Connection = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Browse imported CSV rows: first column split into customer name + address."""
    async with db.execute(
        """SELECT * FROM statement_policy_lines
           ORDER BY id DESC
           LIMIT 5000"""
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


@router.post("/import/statement-lines", response_model=StatementImportStats)
async def statement_import_run(
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create customers and policies for the current user from statement_policy_lines.
    Safe to run more than once: skips rows whose policy_number already exists.
    """
    stats = await materialize_statement_lines(db, user.user_id)
    await db.commit()
    return StatementImportStats(**stats)
