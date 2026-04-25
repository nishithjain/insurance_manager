"""
Tiny cross-cutting helpers shared by every repository module.

Kept private (leading underscore) so they don't show up in IDE auto-import
suggestions for callers — routers should import from the appropriate
domain-specific repository.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException


def parse_customer_id(customer_id: str) -> int:
    """Raise a 404 if the path segment isn't a positive integer — matches legacy behavior."""
    try:
        return int(customer_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Customer not found")


def parse_policy_id(policy_id: str) -> int:
    """Raise a 404 if the path segment isn't a positive integer — matches legacy behavior."""
    try:
        return int(policy_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Policy not found")


def sql_float(v: Any) -> Optional[float]:
    """Best-effort numeric cast for SQLite NUMERIC columns that may contain text."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def maybe_int(v: Any) -> Optional[int]:
    """Best-effort integer cast that returns ``None`` for unparseable values."""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
