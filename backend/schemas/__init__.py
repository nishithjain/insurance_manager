"""
HTTP-facing Pydantic schemas for the Insurance API.

This package replaces the historical single-file ``backend/schemas.py``. The
schemas are now split per domain (auth, customer, policy, statements,
settings, renewal, user) but every previously exported symbol is re-exported
from this top-level module so callers can keep doing
``from schemas import Policy`` without code changes.
"""

from __future__ import annotations

from .admin_taxonomy import (
    InsuranceTypeAdminOut,
    InsuranceTypeCreate,
    InsuranceTypeUpdate,
    PolicyTypeAdminOut,
    PolicyTypeCreate,
    PolicyTypeUpdate,
)
from .auth import (
    AppUser,
    AppUserCreate,
    AppUserStatusUpdate,
    AppUserUpdate,
    DevLoginRequest,
    GoogleLoginRequest,
    TokenResponse,
)
from .customer import Customer, CustomerAdmin, CustomerAdminUpdate, CustomerCreate
from .policy import (
    HealthPolicyDetailsDto,
    InsuranceTypeOut,
    MotorPolicyDetailsDto,
    Policy,
    PolicyContactUpdate,
    PolicyCreate,
    PolicyDetailBundle,
    PolicyPaymentUpdate,
    PolicyRenewalResolutionUpdate,
    PolicyTypeOut,
    PolicyUpdate,
    PolicyUpdateCustomerFields,
    PropertyPolicyDetailsDto,
)
from .renewal import RenewalHistory, RenewalHistoryCreate
from .settings import AppSettings, AppSettingsUpdate
from .statements import (
    StatementCsvUploadOut,
    StatementImportStats,
    StatementPolicyLineOut,
)
from .user import User

__all__ = [
    # admin taxonomy (Insurance Master CRUD)
    "InsuranceTypeAdminOut",
    "InsuranceTypeCreate",
    "InsuranceTypeUpdate",
    "PolicyTypeAdminOut",
    "PolicyTypeCreate",
    "PolicyTypeUpdate",
    # auth
    "AppUser",
    "AppUserCreate",
    "AppUserStatusUpdate",
    "AppUserUpdate",
    "DevLoginRequest",
    "GoogleLoginRequest",
    "TokenResponse",
    # customer
    "Customer",
    "CustomerAdmin",
    "CustomerAdminUpdate",
    "CustomerCreate",
    # policy
    "HealthPolicyDetailsDto",
    "InsuranceTypeOut",
    "MotorPolicyDetailsDto",
    "Policy",
    "PolicyContactUpdate",
    "PolicyCreate",
    "PolicyDetailBundle",
    "PolicyPaymentUpdate",
    "PolicyRenewalResolutionUpdate",
    "PolicyTypeOut",
    "PolicyUpdate",
    "PolicyUpdateCustomerFields",
    "PropertyPolicyDetailsDto",
    # renewal
    "RenewalHistory",
    "RenewalHistoryCreate",
    # settings
    "AppSettings",
    "AppSettingsUpdate",
    # statements
    "StatementCsvUploadOut",
    "StatementImportStats",
    "StatementPolicyLineOut",
    # user
    "User",
]
