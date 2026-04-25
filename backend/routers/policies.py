"""
Policy CRUD + PATCH endpoints + read-only detail bundle.

This module is intentionally thin — every interesting line of business logic
lives in :mod:`services.policy_service`. The router translates HTTP shapes
into service calls and converts :class:`services.policy_service.PolicyServiceError`
into ``HTTPException`` so the application layer never has to import FastAPI.
"""

from __future__ import annotations

from typing import List

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from deps import get_current_user, get_db
from repositories._helpers import parse_policy_id
from schemas import (
    Policy,
    PolicyContactUpdate,
    PolicyCreate,
    PolicyDetailBundle,
    PolicyPaymentUpdate,
    PolicyRenewalResolutionUpdate,
    PolicyUpdate,
    User,
)
from services import policy_service
from services.policy_service import PolicyServiceError

router = APIRouter(tags=["policies"])


def _to_http_exception(err: PolicyServiceError) -> HTTPException:
    """Bridge the application-layer error to FastAPI's HTTP error type."""
    return HTTPException(status_code=err.status_code, detail=err.detail)


@router.get("/policies", response_model=List[Policy])
async def get_policies(
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all policies for current user."""
    return await policy_service.list_policies(db, user.user_id)


@router.post("/policies", response_model=Policy)
async def create_policy(
    policy: PolicyCreate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new policy."""
    try:
        return await policy_service.create_policy(db, user.user_id, policy)
    except PolicyServiceError as err:
        raise _to_http_exception(err) from err


@router.get("/policies/{policy_id}", response_model=Policy)
async def get_policy(
    policy_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific policy."""
    pid = parse_policy_id(policy_id)
    try:
        return await policy_service.get_policy(db, pid, user.user_id)
    except PolicyServiceError as err:
        raise _to_http_exception(err) from err


@router.get("/policies/{policy_id}/detail", response_model=PolicyDetailBundle)
async def get_policy_detail_bundle(
    policy_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Read-only: policy, customer, category group, and motor/health/property rows when present."""
    pid = parse_policy_id(policy_id)
    try:
        return await policy_service.get_policy_detail_bundle(db, pid, user.user_id)
    except PolicyServiceError as err:
        raise _to_http_exception(err) from err


@router.put("/policies/{policy_id}", response_model=Policy)
async def update_policy(
    policy_id: str,
    policy: PolicyUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update a policy and (optionally) the linked customer's contact fields.

    The body extends :class:`PolicyCreate` with an optional ``customer`` block
    (email / phone / address). Customer **name** is intentionally omitted from
    :class:`PolicyUpdateCustomerFields`, so even if a client sends one it is
    discarded by Pydantic before reaching this handler — there is no code
    path here that updates ``customers.full_name``.
    """
    pid = parse_policy_id(policy_id)
    try:
        return await policy_service.update_policy(db, user.user_id, pid, policy)
    except PolicyServiceError as err:
        raise _to_http_exception(err) from err


@router.patch("/policies/{policy_id}/contact", response_model=Policy)
async def patch_policy_contact(
    policy_id: str,
    body: PolicyContactUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update renewal contact fields only (last_contacted_at, contact_status, follow_up_date)."""
    pid = parse_policy_id(policy_id)
    try:
        return await policy_service.update_contact(db, user.user_id, pid, body)
    except PolicyServiceError as err:
        raise _to_http_exception(err) from err


@router.patch("/policies/{policy_id}/payment", response_model=Policy)
async def patch_policy_payment(
    policy_id: str,
    body: PolicyPaymentUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update payment status when current status is PENDING (e.g. mark paid channel)."""
    pid = parse_policy_id(policy_id)
    try:
        return await policy_service.update_payment(db, user.user_id, pid, body)
    except PolicyServiceError as err:
        raise _to_http_exception(err) from err


@router.patch("/policies/{policy_id}/renewal-resolution", response_model=Policy)
async def patch_policy_renewal_resolution(
    policy_id: str,
    body: PolicyRenewalResolutionUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Set renewal resolution for expired / missed-opportunity workflow. Records stay in DB."""
    pid = parse_policy_id(policy_id)
    try:
        return await policy_service.update_renewal_resolution(
            db, user.user_id, pid, body
        )
    except PolicyServiceError as err:
        raise _to_http_exception(err) from err


@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a policy."""
    pid = parse_policy_id(policy_id)
    try:
        return await policy_service.delete_policy(db, user.user_id, pid)
    except PolicyServiceError as err:
        raise _to_http_exception(err) from err
