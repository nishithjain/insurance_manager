"""Pydantic schemas for customer endpoints (per-user and admin grid)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Customer(BaseModel):
    """Per-user customer response (``GET /api/customers``)."""

    id: str
    user_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: str


class CustomerCreate(BaseModel):
    """``POST /api/customers`` body."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class CustomerAdmin(BaseModel):
    """
    Admin-panel response for ``/api/admin/customers``.

    Extends :class:`Customer` with fields the admin grid surfaces (policy
    count, last update timestamp) without altering the per-user
    ``/api/customers`` contract used elsewhere.
    """

    id: str
    user_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    policy_count: int = 0


class CustomerAdminUpdate(BaseModel):
    """Admin → ``PUT /api/admin/customers/{id}``. ``name`` required, others optional."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
