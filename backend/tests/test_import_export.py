"""
Statement-CSV import + data-export tests.

Import side (no FastAPI / aiosqlite — runs through ``sqlite3`` directly):

- Happy path: a small in-memory CSV inserts the expected number of rows into
  ``statement_policy_lines``.
- Unknown header → ``ValueError`` (later mapped to HTTP 400 by the router).
- Mismatched column count → ``ValueError`` (later 400).
- Empty CSV → ``ValueError``.
- ``replace_source=True`` removes prior rows for the same source filename;
  ``replace_source=False`` appends.

Export side (via FastAPI TestClient against the shared app + temp DB):

- ``GET /api/import/statement-lines/summary`` reflects the current row count.
- ``GET /api/statement-lines`` returns the imported rows shaped per the schema.
- ``GET /api/export/policies-csv`` returns a CSV with the UTF-8 BOM and the
  attachment header — and a 400 for an unsupported ``by`` column.
- ``GET /api/export/full-data-zip`` returns a ZIP containing the documented
  member files.
"""

from __future__ import annotations

import importlib
import io
import sqlite3
import sys
import zipfile
from datetime import date

import pytest


# --------------------------------------------------------------------------- #
# Import-side fixture (no FastAPI required)                                   #
# --------------------------------------------------------------------------- #


@pytest.fixture()
def import_module(tmp_path, monkeypatch):
    """
    Re-import :mod:`import_march_statements` against a fresh temp SQLite file.

    The module reads ``db_path.DB_PATH`` and ``services.database_backup`` at
    import time, so we point the env var first, drop cached copies, and then
    let pytest's normal isolation handle teardown.
    """
    db_file = tmp_path / "import.db"
    monkeypatch.setenv("INSURANCE_DB_PATH", str(db_file))
    for mod in ("import_march_statements", "services.database_backup", "db_path"):
        sys.modules.pop(mod, None)
    return importlib.import_module("import_march_statements"), db_file


SAMPLE_HEADER = (
    "NAME AND ADDRESS,PHONE NUMBER,VEHICLE NO,VEHICLE DETAILS,COMPANY,"
    "NCB/DIS,AGENT,IDV OF VEHICLE,ENGINE NO,CHASSIS NO,OD PREMIUM,TP PREMIUM,"
    "PREMIUM,PAYMENT STATUS,DATE OF ISSUE,POLICY END DATE,POLICY NO,CARD DETAILS"
)


def _make_row(name: str, policy_no: str) -> str:
    """Build one CSV row that matches SAMPLE_HEADER's 18 columns."""
    return (
        f"{name},9999900000,KA01AB1234,Honda City,Acme Insurance,"
        "20%,Test Agent,500000,EN-1,CH-1,1000,200,1200,PENDING,"
        f"2026-01-01,2026-12-31,{policy_no},Card-1"
    )


# --------------------------------------------------------------------------- #
# Import: happy path                                                           #
# --------------------------------------------------------------------------- #


def test_import_csv_from_bytes_happy_path(import_module) -> None:
    mod, db_file = import_module
    csv_text = SAMPLE_HEADER + "\n" + _make_row("ALICE TEST", "POL-IMP-001")
    n = mod.import_csv_from_bytes(csv_text.encode("utf-8"), "happy.csv")
    assert n == 1

    conn = sqlite3.connect(str(db_file))
    try:
        rows = conn.execute(
            "SELECT customer_name, policy_number, source_file FROM statement_policy_lines"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "ALICE TEST"
    assert rows[0][1] == "POL-IMP-001"
    assert rows[0][2] == "happy.csv"


def test_import_csv_replaces_prior_rows_for_same_source(import_module) -> None:
    mod, db_file = import_module
    first_csv = (
        SAMPLE_HEADER + "\n" + _make_row("FIRST IMPORT", "POL-FIRST-001")
    ).encode("utf-8")
    second_csv = (
        SAMPLE_HEADER + "\n" + _make_row("SECOND IMPORT", "POL-SECOND-001")
    ).encode("utf-8")

    assert mod.import_csv_from_bytes(first_csv, "stmt.csv") == 1
    assert mod.import_csv_from_bytes(second_csv, "stmt.csv", replace_source=True) == 1

    conn = sqlite3.connect(str(db_file))
    try:
        names = [
            row[0]
            for row in conn.execute(
                "SELECT customer_name FROM statement_policy_lines WHERE source_file = ?",
                ("stmt.csv",),
            )
        ]
    finally:
        conn.close()
    assert names == ["SECOND IMPORT"], "replace_source=True should drop prior rows"


def test_import_csv_append_keeps_prior_rows(import_module) -> None:
    mod, db_file = import_module
    first_csv = (
        SAMPLE_HEADER + "\n" + _make_row("ROW ONE", "POL-AP-001")
    ).encode("utf-8")
    second_csv = (
        SAMPLE_HEADER + "\n" + _make_row("ROW TWO", "POL-AP-002")
    ).encode("utf-8")

    assert mod.import_csv_from_bytes(first_csv, "append.csv") == 1
    assert mod.import_csv_from_bytes(second_csv, "append.csv", replace_source=False) == 1

    conn = sqlite3.connect(str(db_file))
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM statement_policy_lines WHERE source_file = ?",
            ("append.csv",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert n == 2


# --------------------------------------------------------------------------- #
# Import: error paths                                                          #
# --------------------------------------------------------------------------- #


def test_import_csv_xlsx_filename_rejected(import_module) -> None:
    mod, _ = import_module
    with pytest.raises(ValueError, match="csv"):
        mod.import_csv_from_bytes(b"unused", "data.xlsx")


def test_import_csv_unknown_header_rejected(import_module) -> None:
    mod, _ = import_module
    bad = "TOTALLY UNKNOWN COLUMN\nvalue\n"
    with pytest.raises(ValueError, match="Unknown CSV header"):
        mod.import_csv_from_bytes(bad.encode("utf-8"), "bad-header.csv")


def test_import_csv_wrong_column_count_rejected(import_module) -> None:
    mod, _ = import_module
    # Header says 18 columns, row provides 3.
    bad = SAMPLE_HEADER + "\n" + "A,B,C\n"
    with pytest.raises(ValueError, match="Expected"):
        mod.import_csv_from_bytes(bad.encode("utf-8"), "wrong-cols.csv")


def test_import_csv_empty_file_rejected(import_module) -> None:
    mod, _ = import_module
    with pytest.raises(ValueError, match="empty"):
        mod.import_csv_from_bytes(b"", "empty.csv")


def test_import_csv_skips_blank_lines(import_module) -> None:
    """A row of all-empty cells should be silently skipped, not error out."""
    mod, db_file = import_module
    csv_text = (
        SAMPLE_HEADER
        + "\n"
        + _make_row("KEEP ME", "POL-KEEP-001")
        + "\n"
        + ",,,,,,,,,,,,,,,,,,"  # 18 empty fields
    )
    n = mod.import_csv_from_bytes(csv_text.encode("utf-8"), "skip-blank.csv")
    assert n == 1


# --------------------------------------------------------------------------- #
# Export-side tests: TestClient against the shared app                         #
# --------------------------------------------------------------------------- #


def test_statement_lines_endpoints_start_empty(client) -> None:
    r = client.get("/api/import/statement-lines/summary")
    assert r.status_code == 200
    assert r.json() == {"statement_rows": 0}

    r = client.get("/api/statement-lines")
    assert r.status_code == 200
    assert r.json() == []


def test_export_policies_csv_returns_utf8_bom(client, make_customer, make_policy) -> None:
    cust = make_customer(name="Export Owner CSV", phone="6100000001")
    today = date.today()
    make_policy(
        cust["id"],
        policy_number="POL-EXPCSV-001",
        end_date=f"{today.year}-{today.month:02d}-28",
    )

    r = client.get(
        "/api/export/policies-csv",
        params={"year": today.year, "month": today.month, "by": "policy_end_date"},
    )
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers["content-type"]
    assert r.headers["content-disposition"].startswith("attachment;")
    assert r.content.startswith(b"\xef\xbb\xbf"), "expected UTF-8 BOM at file start"


def test_export_policies_csv_rejects_unsupported_by(client) -> None:
    today = date.today()
    r = client.get(
        "/api/export/policies-csv",
        params={"year": today.year, "month": today.month, "by": "definitely-not-a-column"},
    )
    assert r.status_code == 400


def test_export_full_data_zip_contains_expected_members(client) -> None:
    r = client.get("/api/export/full-data-zip")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = set(zf.namelist())

    expected = {
        "customers.csv",
        "customer_addresses.csv",
        "policies.csv",
        "motor_export.csv",
        "health_export.csv",
        "non_motor_export.csv",
        "renewal_history.csv",
        "statement_policy_lines.csv",
        "README.txt",
    }
    missing = expected - names
    assert not missing, f"ZIP missing members: {missing}"
