"""
Admin endpoints to manage authentication users (``app_users`` table).

Every handler depends on :func:`deps.require_admin`, so the router itself does
no role checking. Service-level errors (duplicate email, last-admin protection,
unknown role) are translated to HTTP status codes here and nowhere else.
"""

from __future__ import annotations

from typing import List, Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps import get_db, require_admin
from repositories.app_users import AppUserRepository, AppUserRow
from schemas import AppUser, AppUserCreate, AppUserStatusUpdate, AppUserUpdate
from services.app_user_service import (
    AppUserService,
    DuplicateEmailError,
    LastActiveAdminError,
)


router = APIRouter(tags=["admin-users"])


def _to_dto(row: AppUserRow) -> AppUser:
    return AppUser(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        role=row.role,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        last_login_at=row.last_login_at,
    )


def _service(db: aiosqlite.Connection) -> AppUserService:
    return AppUserService(AppUserRepository(db))


@router.get("/users", response_model=List[AppUser])
async def list_users(
    search: Optional[str] = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> List[AppUser]:
    rows = await _service(db).list_users(search=search, limit=limit, offset=offset)
    return [_to_dto(r) for r in rows]


@router.get("/users/{user_id}", response_model=AppUser)
async def get_user(
    user_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> AppUser:
    row = await _service(db).get_user(user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _to_dto(row)


@router.post("/users", response_model=AppUser, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AppUserCreate,
    db: aiosqlite.Connection = Depends(get_db),
    admin=Depends(require_admin),
) -> AppUser:
    try:
        row = await _service(db).create_user(
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            is_active=payload.is_active,
            created_by=admin.id,
        )
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_dto(row)


@router.put("/users/{user_id}", response_model=AppUser)
async def update_user(
    user_id: int,
    payload: AppUserUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> AppUser:
    try:
        row = await _service(db).update_user(
            user_id=user_id,
            full_name=payload.full_name,
            role=payload.role,
            is_active=payload.is_active,
        )
    except LastActiveAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _to_dto(row)


@router.put("/users/{user_id}/status", response_model=AppUser)
async def set_user_status(
    user_id: int,
    payload: AppUserStatusUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> AppUser:
    try:
        row = await _service(db).set_status(user_id=user_id, is_active=payload.is_active)
    except LastActiveAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _to_dto(row)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    _admin=Depends(require_admin),
) -> dict[str, str]:
    try:
        deleted = await _service(db).delete_user(user_id=user_id)
    except LastActiveAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return {"message": "User deleted."}
