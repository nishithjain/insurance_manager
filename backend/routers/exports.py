"""CSV / ZIP export endpoints (monthly policy CSV + full-data ZIP bundle)."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date, datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from deps import get_current_user, get_db
from domain.dates import parse_date_flexible
from policy_export import (
    EXPORT_POLICIES_CSV_HEADERS,
    build_export_row,
    render_split_csv_rows,
    validate_and_summarize_export,
)
from repositories.sql import EXPORT_POLICY_SELECT
from schemas import User

router = APIRouter(tags=["exports"])


EXPORT_POLICIES_BY_SLUG = {
    "date_of_issue": "month-of-issue",
    "policy_end_date": "expiring",
}

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


def _csv_string_to_utf8_bom_bytes(text: str) -> bytes:
    return ("\ufeff" + text).encode("utf-8")


def _export_row_in_month(row: dict, by: str, year: int, month: int) -> bool:
    if by == "policy_end_date":
        key = "end_date"
    elif by == "date_of_issue":
        key = "start_date"
    else:
        return False
    d = parse_date_flexible(row.get(key))
    if d is None:
        return False
    return d.year == year and d.month == month


async def _export_statement_policy_lines_csv(db: aiosqlite.Connection) -> str:
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


async def _build_full_data_zip_bytes(
    db: aiosqlite.Connection, user_id: str
) -> bytes:
    zip_buf = io.BytesIO()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
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
        zf.writestr(
            "customer_addresses.csv", _csv_string_to_utf8_bom_bytes(abuf.getvalue())
        )

        async with db.execute(
            f"{EXPORT_POLICY_SELECT} WHERE c.user_id = ? "
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
        zf.writestr(
            "renewal_history.csv", _csv_string_to_utf8_bom_bytes(rhbuf.getvalue())
        )

        stmt_csv = await _export_statement_policy_lines_csv(db)
        zf.writestr(
            "statement_policy_lines.csv", _csv_string_to_utf8_bom_bytes(stmt_csv)
        )

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


@router.get("/export/policies-csv")
async def export_policies_csv(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    by: str = Query(
        "policy_end_date",
        description="Month filter: policy_end_date (expiring in that month) or date_of_issue (issued that month)",
    ),
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
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

    async with db.execute(
        f"{EXPORT_POLICY_SELECT} WHERE c.user_id = ? "
        "ORDER BY p.policy_end_date IS NULL, p.policy_end_date ASC, p.policy_id ASC",
        (user.user_id,),
    ) as cursor:
        rows = [dict(r) for r in await cursor.fetchall()]

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
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/full-data-zip")
async def export_full_data_zip(
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    ZIP containing CSV exports: customers, customer_addresses, policies (slim columns + JSON extra_details),
    category split CSVs (motor / health / non-motor), renewal_history, and statement_policy_lines.
    """
    data = await _build_full_data_zip_bytes(db, user.user_id)
    fn = f"insurance_full_export_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )
