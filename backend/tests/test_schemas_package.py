"""
Regression tests for the ``schemas/`` package re-exports.

When ``backend/schemas.py`` was split into a package, every symbol that any
caller (``routers/*``, ``services/*``, ``repositories/*``, the test suite
itself) imported from the old module had to keep working unchanged via the
package's ``__init__.py``. These tests pin that contract so an accidental
deletion or rename in a sub-module surfaces here instead of as a 500 in
production.
"""

from __future__ import annotations

import importlib

import pytest


# Every symbol previously exported by ``schemas.py`` (the single-file module).
# Sourced directly from the public API rather than ``__all__`` so a regression
# is caught even if someone forgets to update ``__all__``.
LEGACY_SYMBOLS = [
    # user
    "User",
    # customer
    "Customer",
    "CustomerCreate",
    "CustomerAdmin",
    "CustomerAdminUpdate",
    # policy / taxonomy
    "InsuranceTypeOut",
    "PolicyTypeOut",
    "Policy",
    "PolicyCreate",
    "PolicyUpdate",
    "PolicyUpdateCustomerFields",
    "PolicyContactUpdate",
    "PolicyRenewalResolutionUpdate",
    "PolicyPaymentUpdate",
    "MotorPolicyDetailsDto",
    "HealthPolicyDetailsDto",
    "PropertyPolicyDetailsDto",
    "PolicyDetailBundle",
    # statements
    "StatementPolicyLineOut",
    "StatementImportStats",
    "StatementCsvUploadOut",
    # settings
    "AppSettings",
    "AppSettingsUpdate",
    # renewal
    "RenewalHistory",
    "RenewalHistoryCreate",
    # auth
    "AppUser",
    "AppUserCreate",
    "AppUserUpdate",
    "AppUserStatusUpdate",
    "GoogleLoginRequest",
    "DevLoginRequest",
    "TokenResponse",
]


@pytest.mark.parametrize("symbol", LEGACY_SYMBOLS)
def test_legacy_symbol_is_reexported(symbol: str) -> None:
    """Every old ``from schemas import X`` keeps working."""
    schemas = importlib.import_module("schemas")
    assert hasattr(schemas, symbol), f"schemas.{symbol} is missing"


def test_policy_update_inherits_from_policy_create() -> None:
    """The PolicyUpdate ↔ PolicyCreate inheritance is part of the public contract."""
    schemas = importlib.import_module("schemas")
    assert issubclass(schemas.PolicyUpdate, schemas.PolicyCreate)


def test_policy_update_customer_block_is_optional_and_drops_name() -> None:
    """
    The customer block on ``PolicyUpdate`` must stay optional and must NOT
    accept a ``name`` field — that constraint is the only thing standing
    between the policy edit modal and an accidental customer rename.
    """
    schemas = importlib.import_module("schemas")
    update = schemas.PolicyUpdate(
        customer_id="c1",
        policy_number="P1",
        policy_type="Motor",
        start_date="2025-01-01",
        end_date="2026-01-01",
        premium=1.0,
        customer={"email": "x@y.z", "phone": "1", "address": "A", "name": "Hacker"},
    )
    assert update.customer is not None
    assert not hasattr(update.customer, "name")


def test_appuser_create_rejects_short_name() -> None:
    """``AppUserCreate.full_name`` keeps the historical 1..200 length bound."""
    schemas = importlib.import_module("schemas")
    with pytest.raises(Exception):
        schemas.AppUserCreate(email="a@b.co", full_name="", role="admin")


def test_token_response_default_token_type() -> None:
    """``TokenResponse.token_type`` defaults to ``Bearer``."""
    schemas = importlib.import_module("schemas")
    user = schemas.AppUser(
        id=1,
        email="a@b.co",
        full_name="A",
        role="admin",
        is_active=True,
        created_at="t",
        updated_at="t",
    )
    resp = schemas.TokenResponse(access_token="t", expires_at="t", user=user)
    assert resp.token_type == "Bearer"
