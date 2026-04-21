"""
Import MARCH STATEMENTS 2026.csv (or similar) into statement_policy_lines.
Uses csv module so multiline quoted address fields parse correctly.

First column (NAME AND ADDRESS): first line = customer name, remaining lines = address.

The web dashboard reads customers + policies, not this staging table. After import,
open the dashboard and click **Load CSV rows into dashboard**, or call
POST /api/import/statement-lines with your session.

Usage (from backend/):
  import_statements.bat
  import_statements.bat "..\\MARCH STATEMENTS 2026.csv"
  ./import_statements.sh "../MARCH STATEMENTS 2026.csv"

If you see ``No module named 'encodings'``, your shell set PYTHONHOME (e.g. from BMC Python).
Either run the wrappers above, or: ``unset PYTHONHOME`` in Git Bash, then use
``.venv/Scripts/python.exe import_march_statements.py ...`` from backend/.
"""
from __future__ import annotations

import argparse
import csv
import io
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from statement_parse import split_name_address
from db_path import DB_PATH


def _resolve_csv_path(arg: str) -> Path:
    """
    Resolve CSV path whether you run the script from repo root or backend/, and whether you pass
    ``../MARCH STATEMENTS 2026.csv`` or ``MARCH STATEMENTS 2026.csv`` (repo root file).
    """
    raw = Path(arg)
    if raw.is_file():
        return raw.resolve()
    here = Path(__file__).resolve().parent
    repo = here.parent
    candidates = [
        Path.cwd() / raw,
        here / raw,
        repo / raw,
        repo / raw.name,
    ]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    return (Path.cwd() / raw).resolve()

HEADER_TO_COLUMN = {
    "NAME AND ADDRESS": "name_and_address_raw",
    "PHONE NUMBER": "phone_number",
    "VEHICLE NO": "vehicle_registration",
    "VEHICLE DETAILS": "vehicle_details",
    "COMPANY": "insurer_company",
    "NCB/DIS": "ncb_or_discount",
    "AGENT": "agent",
    "IDV OF VEHICLE": "idv",
    "ENGINE NO": "engine_no",
    "CHASSIS NO": "chassis_no",
    "OD PREMIUM": "od_premium",
    "TP PREMIUM": "tp_premium",
    "PREMIUM": "premium_total",
    "PAYMENT STATUS": "payment_status",
    "DATE OF ISSUE": "date_of_issue",
    "POLICY END DATE": "policy_end_date",
    "POLICY NO": "policy_number",
    "CARD DETAILS": "card_details",
}


def _norm(h: str) -> str:
    return " ".join(h.strip().split()).upper()


def _header_map(raw_headers: list[str]) -> list[str]:
    out = []
    for h in raw_headers:
        key = _norm(h)
        if key.startswith("VEHICLE DETAILS"):
            key = "VEHICLE DETAILS"
        col = HEADER_TO_COLUMN.get(key)
        if col is None:
            raise ValueError(f"Unknown CSV header {h!r} (normalized {key!r})")
        out.append(col)
    return out


def _cell(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.strip()
    return s if s else None


def _ensure_statement_table(conn: sqlite3.Connection) -> set[str]:
    """Create or upgrade statement_policy_lines; return current column names."""
    conn.execute(
        """
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
        )
        """
    )
    cur = conn.execute("PRAGMA table_info(statement_policy_lines)")
    cols = {r[1] for r in cur.fetchall()}
    if "customer_name" not in cols:
        conn.execute("ALTER TABLE statement_policy_lines ADD COLUMN customer_name TEXT")
        conn.execute("ALTER TABLE statement_policy_lines ADD COLUMN address TEXT")
        cols |= {"customer_name", "address"}
    if "name_and_address" in cols:
        cur2 = conn.execute(
            "SELECT id, name_and_address FROM statement_policy_lines WHERE name_and_address IS NOT NULL"
        )
        for rid, na in cur2.fetchall():
            name, addr = split_name_address(na)
            conn.execute(
                "UPDATE statement_policy_lines SET customer_name = ?, address = ? WHERE id = ?",
                (name, addr, rid),
            )
    cur = conn.execute("PRAGMA table_info(statement_policy_lines)")
    return {r[1] for r in cur.fetchall()}


def _parse_csv_reader(reader: csv.reader, source_file: str) -> list[tuple]:
    """Build row tuples; each ends with (source_file, imported_at)."""
    imported_at = datetime.now(timezone.utc).isoformat()
    try:
        raw_header = next(reader)
    except StopIteration:
        raise ValueError("CSV is empty")

    columns = _header_map(raw_header)
    rows_to_insert: list[tuple] = []
    for row in reader:
        if not row or all(not (c or "").strip() for c in row):
            continue
        if len(row) != len(columns):
            raise ValueError(
                f"Expected {len(columns)} columns, got {len(row)}: {row[:4]}..."
            )
        d = dict(zip(columns, row))
        raw_na = d.get("name_and_address_raw") or ""
        raw_cell = _cell(raw_na) or ""
        cust_name, addr = split_name_address(raw_cell if raw_cell else None)
        rows_to_insert.append(
            (
                cust_name,
                addr,
                raw_cell,
                _cell(d.get("phone_number")),
                _cell(d.get("vehicle_registration")),
                _cell(d.get("vehicle_details")),
                _cell(d.get("insurer_company")),
                _cell(d.get("ncb_or_discount")),
                _cell(d.get("agent")),
                _cell(d.get("idv")),
                _cell(d.get("engine_no")),
                _cell(d.get("chassis_no")),
                _cell(d.get("od_premium")),
                _cell(d.get("tp_premium")),
                _cell(d.get("premium_total")),
                _cell(d.get("payment_status")),
                _cell(d.get("date_of_issue")),
                _cell(d.get("policy_end_date")),
                _cell(d.get("policy_number")),
                _cell(d.get("card_details")),
                source_file,
                imported_at,
            )
        )
    return rows_to_insert


def _save_statement_rows(
    rows_to_insert: list[tuple],
    source_file: str,
    *,
    replace_source: bool,
) -> int:
    """Row tuples end with source_file, imported_at."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        table_cols = _ensure_statement_table(conn)

        if replace_source:
            conn.execute(
                "DELETE FROM statement_policy_lines WHERE source_file = ?",
                (source_file,),
            )

        legacy = "name_and_address" in table_cols

        for tup in rows_to_insert:
            (
                cust_name,
                addr,
                raw_cell,
                phone_number,
                vehicle_registration,
                vehicle_details,
                insurer_company,
                ncb_or_discount,
                agent,
                idv,
                engine_no,
                chassis_no,
                od_premium,
                tp_premium,
                premium_total,
                payment_status,
                date_of_issue,
                policy_end_date,
                policy_number,
                card_details,
                sf,
                imp_at,
            ) = tup

            if legacy:
                na_legacy = raw_cell if raw_cell else cust_name
                conn.execute(
                    """
                    INSERT INTO statement_policy_lines (
                        customer_name, address, name_and_address,
                        phone_number, vehicle_registration, vehicle_details,
                        insurer_company, ncb_or_discount, agent, idv, engine_no, chassis_no,
                        od_premium, tp_premium, premium_total, payment_status,
                        date_of_issue, policy_end_date, policy_number, card_details,
                        source_file, imported_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        cust_name,
                        addr,
                        na_legacy,
                        phone_number,
                        vehicle_registration,
                        vehicle_details,
                        insurer_company,
                        ncb_or_discount,
                        agent,
                        idv,
                        engine_no,
                        chassis_no,
                        od_premium,
                        tp_premium,
                        premium_total,
                        payment_status,
                        date_of_issue,
                        policy_end_date,
                        policy_number,
                        card_details,
                        sf,
                        imp_at,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO statement_policy_lines (
                        customer_name, address,
                        phone_number, vehicle_registration, vehicle_details,
                        insurer_company, ncb_or_discount, agent, idv, engine_no, chassis_no,
                        od_premium, tp_premium, premium_total, payment_status,
                        date_of_issue, policy_end_date, policy_number, card_details,
                        source_file, imported_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        cust_name,
                        addr,
                        phone_number,
                        vehicle_registration,
                        vehicle_details,
                        insurer_company,
                        ncb_or_discount,
                        agent,
                        idv,
                        engine_no,
                        chassis_no,
                        od_premium,
                        tp_premium,
                        premium_total,
                        payment_status,
                        date_of_issue,
                        policy_end_date,
                        policy_number,
                        card_details,
                        sf,
                        imp_at,
                    ),
                )

        conn.commit()
    finally:
        conn.close()

    return len(rows_to_insert)


def import_csv(csv_path: Path, *, replace_source: bool = True) -> int:
    """Read a CSV file from disk and insert rows into statement_policy_lines."""
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)
    if csv_path.suffix.lower() == ".xlsx":
        raise ValueError(
            "This importer expects a .csv file. Export the spreadsheet as CSV from Excel."
        )
    source_file = csv_path.name
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = _parse_csv_reader(reader, source_file)
    return _save_statement_rows(rows, source_file, replace_source=replace_source)


def import_csv_from_bytes(
    data: bytes, source_file: str, *, replace_source: bool = True
) -> int:
    """Parse CSV bytes (e.g. from multipart upload) and insert into statement_policy_lines."""
    if source_file.lower().endswith(".xlsx"):
        raise ValueError(
            "This importer expects a .csv file. Export the spreadsheet as CSV from Excel."
        )
    text = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = _parse_csv_reader(reader, source_file)
    return _save_statement_rows(rows, source_file, replace_source=replace_source)


def main() -> None:
    default_csv = Path(__file__).resolve().parent.parent / "MARCH STATEMENTS 2026.csv"
    p = argparse.ArgumentParser(description="Import March statements CSV into SQLite")
    p.add_argument(
        "csv_path",
        nargs="?",
        default=str(default_csv),
        help=f"Path to CSV (default: {default_csv})",
    )
    p.add_argument(
        "--append",
        action="store_true",
        help="Do not delete existing rows for this source_file before import",
    )
    args = p.parse_args()
    path = _resolve_csv_path(args.csv_path)
    if path.suffix.lower() == ".xlsx":
        print(
            "Error: This importer expects a .csv file. Export the spreadsheet as CSV from Excel, "
            "or pass the path to MARCH STATEMENTS 2026.csv.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        n = import_csv(path, replace_source=not args.append)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print(f"  CSV tried: {path}", file=sys.stderr)
        print(f"  Database:  {DB_PATH.resolve()}", file=sys.stderr)
        sys.exit(1)
    print(f"Imported {n} rows into {DB_PATH.resolve()} (source_file={path.name!r})")


if __name__ == "__main__":
    main()
