"""
Insurance / Policy taxonomy endpoints.

Powers the cascading "Insurance Type → Policy Type" dropdowns in the web
frontend. The API uses the user-visible names ("Insurance Type" /
"Policy Type"); under the hood the parent rows live in
``insurance_categories`` and the child rows in ``policy_types``. See
``database.py`` for the schema and seed data.

All endpoints require an authenticated user — they're read-only master data
so any logged-in user can fetch them (mobile included, even though Android
currently doesn't call them).
"""

from __future__ import annotations

from typing import List, Optional

import aiosqlite
from fastapi import APIRouter, Depends, Query

from deps import get_current_user, get_db
from schemas import InsuranceTypeOut, PolicyTypeOut, User

router = APIRouter(tags=["types"])


@router.get("/insurance-types", response_model=List[InsuranceTypeOut])
async def list_insurance_types(
    include_inactive: bool = Query(False, description="Include archived rows"),
    db: aiosqlite.Connection = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return all insurance categories (Motor, Health, Life, ...)."""
    where = "" if include_inactive else "WHERE is_active = 1"
    async with db.execute(
        f"SELECT id, name, is_active FROM insurance_categories {where} "
        "ORDER BY name COLLATE NOCASE"
    ) as cursor:
        rows = await cursor.fetchall()
    return [
        InsuranceTypeOut(
            id=int(r["id"]),
            name=str(r["name"]),
            is_active=bool(r["is_active"]),
        )
        for r in rows
    ]


@router.get("/policy-types", response_model=List[PolicyTypeOut])
async def list_policy_types(
    insurance_type_id: Optional[int] = Query(
        None,
        description=(
            "When set, return only policy types under the given insurance "
            "category (parent). Maps to ``insurance_categories.id``."
        ),
    ),
    include_inactive: bool = Query(False, description="Include archived rows"),
    db: aiosqlite.Connection = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return policy types, optionally filtered to a single insurance category."""
    clauses: list[str] = []
    params: list = []
    if insurance_type_id is not None:
        clauses.append("insurance_category_id = ?")
        params.append(insurance_type_id)
    if not include_inactive:
        clauses.append("is_active = 1")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    async with db.execute(
        f"""SELECT id, insurance_category_id, name, is_active
            FROM policy_types {where}
            ORDER BY name COLLATE NOCASE""",
        tuple(params),
    ) as cursor:
        rows = await cursor.fetchall()
    return [
        PolicyTypeOut(
            id=int(r["id"]),
            insurance_type_id=int(r["insurance_category_id"]),
            name=str(r["name"]),
            is_active=bool(r["is_active"]),
        )
        for r in rows
    ]
