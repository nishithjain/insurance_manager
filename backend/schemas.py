"""
All HTTP-facing Pydantic schemas for the Insurance API.

Previously colocated at the top of ``server.py``. Centralizing them here keeps the
route modules focused on handler logic and makes the wire contract easy to audit
in one place.

Naming follows FastAPI convention — ``*Create`` / ``*Update`` are request bodies,
plain model names are response bodies.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


# ============= USER =============

class User(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    created_at: str


# ============= CUSTOMER =============

class Customer(BaseModel):
    id: str
    user_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: str


class CustomerCreate(BaseModel):
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
    """Admin → PUT /api/admin/customers/{id}. ``name`` required, others optional."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


# ============= POLICY =============

class Policy(BaseModel):
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


class PolicyCreate(BaseModel):
    customer_id: str
    policy_number: str
    policy_type: str
    start_date: str
    end_date: str
    premium: float
    status: str = "active"


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
    PUT /api/policies/{id} body.

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


# ============= POLICY DETAIL BUNDLE (mobile read-only) =============

class MotorPolicyDetailsDto(BaseModel):
    """Subset of motor_policy_details for mobile read-only detail."""

    vehicle_no: Optional[str] = None
    vehicle_details: Optional[str] = None
    idv_of_vehicle: Optional[float] = None
    engine_no: Optional[str] = None
    chassis_no: Optional[str] = None
    od_premium: Optional[float] = None
    tp_premium: Optional[float] = None


class HealthPolicyDetailsDto(BaseModel):
    """Subset of health_policy_details for mobile read-only detail."""

    plan_name: Optional[str] = None
    sum_insured: Optional[float] = None
    cover_type: Optional[str] = None
    members_covered: Optional[str] = None
    base_premium: Optional[float] = None
    additional_premium: Optional[float] = None


class PropertyPolicyDetailsDto(BaseModel):
    """Subset of property_policy_details for mobile read-only detail."""

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


# ============= STATEMENT IMPORT =============

class StatementPolicyLineOut(BaseModel):
    """One row from imported statement CSV (staging table)."""

    id: int
    customer_name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    vehicle_registration: Optional[str] = None
    vehicle_details: Optional[str] = None
    insurer_company: Optional[str] = None
    policy_number: Optional[str] = None
    premium_total: Optional[str] = None
    payment_status: Optional[str] = None
    date_of_issue: Optional[str] = None
    policy_end_date: Optional[str] = None
    source_file: str
    imported_at: str


class StatementImportStats(BaseModel):
    """Result of promoting statement_policy_lines into customers + policies."""

    statement_rows: int
    customers_created: int
    policies_created: int
    policies_skipped: int


class StatementCsvUploadOut(BaseModel):
    """Result of uploading a statement CSV into statement_policy_lines."""

    rows_inserted: int
    source_file: str
    replace_existing: bool
    materialize: Optional[StatementImportStats] = None


# ============= APP SETTINGS =============

class AppSettings(BaseModel):
    database_backup_folder: Optional[str] = None


class AppSettingsUpdate(BaseModel):
    database_backup_folder: Optional[str] = None


# ============= RENEWAL HISTORY =============

class RenewalHistory(BaseModel):
    id: str
    policy_id: str
    renewal_date: str
    amount: float
    status: str
    created_at: str


class RenewalHistoryCreate(BaseModel):
    policy_id: str
    renewal_date: str
    amount: float
    status: str = "completed"


# ============= AUTH (app_users) =============
#
# These are the HTTP-facing schemas for authentication and admin user management.
# ``AppUser`` is the response shape returned from every user-facing endpoint; it
# intentionally omits fields that only exist for storage bookkeeping.
#
# Note: Pydantic BaseModel already rejects unknown fields during validation of
# request bodies — so a client trying to forge ``id`` / ``created_at`` on a
# create payload will be ignored cleanly, not silently accepted.


from pydantic import EmailStr, Field  # noqa: E402 — keep auth imports colocated


class AppUser(BaseModel):
    """
    Admin-panel and /auth/me response shape.

    ``email`` is plain ``str`` on the response side because the stored value
    has already been verified (either by Google Sign-In or by strict
    ``EmailStr`` validation on :class:`AppUserCreate`). Re-validating on read
    would reject legitimate internal-TLD addresses that strict validators
    classify as "special-use".
    """

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str
    created_by: Optional[int] = None
    last_login_at: Optional[str] = None


class AppUserCreate(BaseModel):
    """Admin → POST /api/users body."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    role: str = Field(description="'admin' or 'user'")
    is_active: bool = True


class AppUserUpdate(BaseModel):
    """Admin → PUT /api/users/{id} body. All fields optional (partial update)."""

    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    role: Optional[str] = None
    is_active: Optional[bool] = None


class AppUserStatusUpdate(BaseModel):
    """Admin → PUT /api/users/{id}/status body."""

    is_active: bool


class GoogleLoginRequest(BaseModel):
    """POST /api/auth/google — client trades Google ID token for our JWT."""

    id_token: str = Field(min_length=16)


class DevLoginRequest(BaseModel):
    """
    POST /api/auth/dev-login — dev-only shortcut to mint a session by email.

    Only honored when the backend has ``ALLOW_DEV_AUTH=true``. Useful for
    emulators / CI where configuring a real Google account is impractical.
    """

    email: str = Field(min_length=3, max_length=320)


class TokenResponse(BaseModel):
    """Successful login response. ``user`` included so the client can skip /me."""

    access_token: str
    token_type: str = "Bearer"
    expires_at: str
    user: AppUser
