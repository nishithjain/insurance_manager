"""
Pydantic schemas for policies, the two-layer insurance taxonomy, and the
mobile read-only policy detail bundle.

Naming follows FastAPI convention — ``*Create`` / ``*Update`` are request
bodies, plain model names are response bodies.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .customer import Customer


# --------------------------------------------------------------------------- #
# Two-layer insurance taxonomy                                                #
# --------------------------------------------------------------------------- #
#
# Added in the insurance/policy-type refactor:
#   InsuranceTypeOut → master row from ``insurance_categories``
#                      (Motor, Health, Life, Travel, Property)
#   PolicyTypeOut    → master row from ``policy_types`` (specific variant)
#
# Existing ``Policy.policy_type`` (text) is kept untouched for back-compat
# with the Android client and CSV exports — it still carries the legacy
# ``insurance_types.insurance_type_name`` value.


class InsuranceTypeOut(BaseModel):
    """Parent category (a.k.a. "Insurance Type")."""

    id: int
    name: str
    is_active: bool = True


class PolicyTypeOut(BaseModel):
    """Specific variant under an insurance type."""

    id: int
    insurance_type_id: int
    name: str
    is_active: bool = True


# --------------------------------------------------------------------------- #
# Policy core                                                                 #
# --------------------------------------------------------------------------- #


class Policy(BaseModel):
    """Full policy response shape used everywhere a policy is read."""

    id: str
    user_id: str
    customer_id: str
    policy_number: str
    policy_type: str
    insurer_company: Optional[str] = None
    payment_status: Optional[str] = None
    payment_note: Optional[str] = None
    payment_updated_at: Optional[str] = None
    start_date: str
    end_date: str
    premium: float
    status: str
    created_at: str
    last_contacted_at: Optional[str] = None
    contact_status: str = "Not Contacted"
    follow_up_date: Optional[str] = None
    renewal_status: str = "Open"
    renewal_resolution_note: Optional[str] = None
    renewal_resolved_at: Optional[str] = None
    renewal_resolved_by: Optional[str] = None
    insurance_type_id: Optional[int] = None
    insurance_type_name: Optional[str] = None
    policy_type_id: Optional[int] = None
    policy_type_name: Optional[str] = None


class PolicyCreate(BaseModel):
    """``POST /api/policies`` body."""

    customer_id: str
    policy_number: str
    policy_type: str
    start_date: str
    end_date: str
    premium: float
    status: str = "active"
    insurance_type_id: Optional[int] = None
    policy_type_id: Optional[int] = None


class PolicyUpdateCustomerFields(BaseModel):
    """
    Editable customer fields embedded in :class:`PolicyUpdate`.

    Deliberately does NOT include ``name`` — the customer name is read-only
    in the policy edit modal. Any ``name`` key sent by a client is silently
    dropped by Pydantic's default ``extra='ignore'`` behavior, so the backend
    cannot be tricked into renaming the customer through this endpoint.
    """

    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class PolicyUpdate(PolicyCreate):
    """
    ``PUT /api/policies/{id}`` body.

    Mirrors :class:`PolicyCreate` for the policy row itself and adds an
    optional ``customer`` block so the edit modal can update the linked
    customer's contact details in the same round-trip. When ``customer`` is
    omitted (e.g. mobile clients), no customer-side write is performed —
    behavior is identical to the prior contract.
    """

    customer: Optional[PolicyUpdateCustomerFields] = None


class PolicyContactUpdate(BaseModel):
    """Partial update for renewal contact tracking (PATCH). Omitted fields are left unchanged."""

    last_contacted_at: Optional[str] = None
    contact_status: Optional[str] = None
    follow_up_date: Optional[str] = None


class PolicyRenewalResolutionUpdate(BaseModel):
    """Resolve or reopen expired-policy renewal workflow (PATCH)."""

    renewal_status: str
    renewal_resolution_note: Optional[str] = None


class PolicyPaymentUpdate(BaseModel):
    """Set payment status when clearing a PENDING row (PATCH)."""

    payment_status: str
    payment_note: Optional[str] = None


# --------------------------------------------------------------------------- #
# Policy detail bundle (Android read-only)                                    #
# --------------------------------------------------------------------------- #


class MotorPolicyDetailsDto(BaseModel):
    """Subset of ``motor_policy_details`` for mobile read-only detail."""

    vehicle_no: Optional[str] = None
    vehicle_details: Optional[str] = None
    idv_of_vehicle: Optional[float] = None
    engine_no: Optional[str] = None
    chassis_no: Optional[str] = None
    od_premium: Optional[float] = None
    tp_premium: Optional[float] = None


class HealthPolicyDetailsDto(BaseModel):
    """Subset of ``health_policy_details`` for mobile read-only detail."""

    plan_name: Optional[str] = None
    sum_insured: Optional[float] = None
    cover_type: Optional[str] = None
    members_covered: Optional[str] = None
    base_premium: Optional[float] = None
    additional_premium: Optional[float] = None


class PropertyPolicyDetailsDto(BaseModel):
    """Subset of ``property_policy_details`` for mobile read-only detail."""

    product_name: Optional[str] = None
    sum_insured: Optional[float] = None
    sub_product: Optional[str] = None
    risk_location: Optional[str] = None
    base_premium: Optional[float] = None
    additional_premium: Optional[float] = None


class PolicyDetailBundle(BaseModel):
    """Policy + customer + insurance category + optional line-of-business details."""

    policy: Policy
    customer: Customer
    category_group: str
    motor: Optional[MotorPolicyDetailsDto] = None
    health: Optional[HealthPolicyDetailsDto] = None
    property_detail: Optional[PropertyPolicyDetailsDto] = None
