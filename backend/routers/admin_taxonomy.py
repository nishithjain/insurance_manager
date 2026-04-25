"""
Admin CRUD endpoints for the "Insurance Master" page.

Two route groups, both gated by :func:`deps.require_admin`:

* ``/api/admin/insurance-types`` — manages ``insurance_categories`` rows
  (parent: Motor, Health, Life, ...).
* ``/api/admin/policy-types`` — manages ``policy_types`` rows
  (children: Private Car, Family Floater, Term Life, ...).

Delete is "smart": rows still referenced by a policy are soft-deactivated,
unused rows are hard-deleted. The response always tells the admin which path
was taken so the UI can surface a clear toast.
"""

from __future__ import annotations

from typing import List, Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps import get_db, require_admin
from repositories import insurance_master_repo as repo
from schemas import (
    InsuranceTypeAdminOut,
    InsuranceTypeCreate,
    InsuranceTypeUpdate,
    PolicyTypeAdminOut,
    PolicyTypeCreate,
    PolicyTypeUpdate,
)


router = APIRouter(tags=["admin-taxonomy"])


def _to_insurance_dto(row: dict) -> InsuranceTypeAdminOut:
    return InsuranceTypeAdminOut(**row)


def _to_policy_type_dto(row: dict) -> PolicyTypeAdminOut:
    return PolicyTypeAdminOut(**row)


def _translate(error: repo.InsuranceMasterError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.message)


# --------------------------------------------------------------------------- #
# Insurance Types                                                             #
# --------------------------------------------------------------------------- #


@router.get(
    "/admin/insurance-types",
    response_model=List[InsuranceTypeAdminOut],
)
async def admin_list_insurance_types(
    include_inactive: bool = Query(True),
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> List[InsuranceTypeAdminOut]:
    rows = await repo.list_insurance_types(db, include_inactive=include_inactive)
    return [_to_insurance_dto(r) for r in rows]


@router.get(
    "/admin/insurance-types/{type_id}",
    response_model=InsuranceTypeAdminOut,
)
async def admin_get_insurance_type(
    type_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> InsuranceTypeAdminOut:
    row = await repo.get_insurance_type(db, type_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance Type not found.",
        )
    return _to_insurance_dto(row)


@router.post(
    "/admin/insurance-types",
    response_model=InsuranceTypeAdminOut,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_insurance_type(
    payload: InsuranceTypeCreate,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> InsuranceTypeAdminOut:
    try:
        row = await repo.create_insurance_type(
            db,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
        )
    except repo.InsuranceMasterError as exc:
        raise _translate(exc) from exc
    return _to_insurance_dto(row)


@router.put(
    "/admin/insurance-types/{type_id}",
    response_model=InsuranceTypeAdminOut,
)
async def admin_update_insurance_type(
    type_id: int,
    payload: InsuranceTypeUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> InsuranceTypeAdminOut:
    sent = payload.model_dump(exclude_unset=True)
    try:
        row = await repo.update_insurance_type(
            db,
            type_id=type_id,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
            description_was_set="description" in sent,
        )
    except repo.InsuranceMasterError as exc:
        raise _translate(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance Type not found.",
        )
    return _to_insurance_dto(row)


@router.delete("/admin/insurance-types/{type_id}")
async def admin_delete_insurance_type(
    type_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> dict:
    outcome, row = await repo.delete_insurance_type(db, type_id)
    if outcome == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance Type not found.",
        )
    if outcome == "deactivated":
        return {
            "outcome": "deactivated",
            "message": (
                "Insurance Type is in use by existing policies and was "
                "deactivated instead of deleted."
            ),
            "item": _to_insurance_dto(row).model_dump() if row else None,
        }
    return {
        "outcome": "deleted",
        "message": "Insurance Type deleted.",
        "item": None,
    }


# --------------------------------------------------------------------------- #
# Policy Types                                                                #
# --------------------------------------------------------------------------- #


@router.get(
    "/admin/policy-types",
    response_model=List[PolicyTypeAdminOut],
)
async def admin_list_policy_types(
    insurance_type_id: Optional[int] = Query(default=None, ge=1),
    include_inactive: bool = Query(True),
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> List[PolicyTypeAdminOut]:
    rows = await repo.list_policy_types(
        db,
        insurance_type_id=insurance_type_id,
        include_inactive=include_inactive,
    )
    return [_to_policy_type_dto(r) for r in rows]


@router.get(
    "/admin/policy-types/{policy_type_id}",
    response_model=PolicyTypeAdminOut,
)
async def admin_get_policy_type(
    policy_type_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> PolicyTypeAdminOut:
    row = await repo.get_policy_type(db, policy_type_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy Type not found.",
        )
    return _to_policy_type_dto(row)


@router.post(
    "/admin/policy-types",
    response_model=PolicyTypeAdminOut,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_policy_type(
    payload: PolicyTypeCreate,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> PolicyTypeAdminOut:
    try:
        row = await repo.create_policy_type(
            db,
            insurance_type_id=payload.insurance_type_id,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
        )
    except repo.InsuranceMasterError as exc:
        raise _translate(exc) from exc
    return _to_policy_type_dto(row)


@router.put(
    "/admin/policy-types/{policy_type_id}",
    response_model=PolicyTypeAdminOut,
)
async def admin_update_policy_type(
    policy_type_id: int,
    payload: PolicyTypeUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> PolicyTypeAdminOut:
    sent = payload.model_dump(exclude_unset=True)
    try:
        row = await repo.update_policy_type(
            db,
            policy_type_id=policy_type_id,
            insurance_type_id=payload.insurance_type_id,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
            description_was_set="description" in sent,
        )
    except repo.InsuranceMasterError as exc:
        raise _translate(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy Type not found.",
        )
    return _to_policy_type_dto(row)


@router.delete("/admin/policy-types/{policy_type_id}")
async def admin_delete_policy_type(
    policy_type_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> dict:
    outcome, row = await repo.delete_policy_type(db, policy_type_id)
    if outcome == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy Type not found.",
        )
    if outcome == "deactivated":
        return {
            "outcome": "deactivated",
            "message": (
                "Policy Type is in use by existing policies and was "
                "deactivated instead of deleted."
            ),
            "item": _to_policy_type_dto(row).model_dump() if row else None,
        }
    return {
        "outcome": "deleted",
        "message": "Policy Type deleted.",
        "item": None,
    }
