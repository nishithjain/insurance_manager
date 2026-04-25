"""
Unit tests for :mod:`services.policy_service`.

These exercise the application-layer rules (taxonomy resolution, validation,
authorisation orchestration) without touching SQLite. Anywhere a repository
function would normally hit the DB we patch the call site so the test stays
fast and isolated.

The DB-end-to-end coverage of the same flows lives in ``test_api_smoke.py``,
which spins up the whole app against a temp SQLite file.
"""

from __future__ import annotations

import asyncio
import importlib
from unittest.mock import AsyncMock, patch

import pytest

policy_service = importlib.import_module("services.policy_service")
schemas = importlib.import_module("schemas")

PolicyServiceError = policy_service.PolicyServiceError


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# Error class                                                                 #
# --------------------------------------------------------------------------- #


def test_policy_service_error_carries_status_and_detail() -> None:
    err = PolicyServiceError(404, "Policy not found")
    assert err.status_code == 404
    assert err.detail == "Policy not found"
    assert str(err) == "Policy not found"


# --------------------------------------------------------------------------- #
# Customer-id parsing                                                         #
# --------------------------------------------------------------------------- #


def test_parse_customer_pk_rejects_non_integer() -> None:
    with pytest.raises(PolicyServiceError) as exc:
        policy_service._parse_customer_pk("abc")
    assert exc.value.status_code == 404
    assert "Customer not found" in exc.value.detail


def test_parse_customer_pk_accepts_numeric_string() -> None:
    assert policy_service._parse_customer_pk("42") == 42


# --------------------------------------------------------------------------- #
# Taxonomy resolution                                                         #
# --------------------------------------------------------------------------- #


def test_resolve_taxonomy_uses_new_policy_type_when_provided() -> None:
    """When ``policy_type_id`` is sent we must look up its parent and derive both FKs."""

    async def go():
        with patch.object(
            policy_service, "get_policy_type_with_category", new=AsyncMock()
        ) as get_pt, patch.object(
            policy_service, "resolve_legacy_insurance_type_for_category", new=AsyncMock()
        ) as legacy, patch.object(
            policy_service, "resolve_insurance_type_id", new=AsyncMock()
        ) as legacy_slug:
            get_pt.return_value = {
                "id": 7,
                "name": "Comprehensive",
                "is_active": 1,
                "insurance_category_id": 1,
                "insurance_category_name": "Motor",
            }
            legacy.return_value = 99
            return await policy_service._resolve_taxonomy(
                db=object(),
                policy_type_id=7,
                insurance_type_id=1,
                legacy_policy_type="auto",
            ), legacy_slug

    (legacy_id, new_pt_id), legacy_slug = _run(go())
    assert legacy_id == 99
    assert new_pt_id == 7
    legacy_slug.assert_not_awaited()  # legacy slug path skipped


def test_resolve_taxonomy_rejects_unknown_policy_type_id() -> None:
    async def go():
        with patch.object(
            policy_service, "get_policy_type_with_category", new=AsyncMock()
        ) as get_pt:
            get_pt.return_value = None
            await policy_service._resolve_taxonomy(
                db=object(),
                policy_type_id=999,
                insurance_type_id=None,
                legacy_policy_type="auto",
            )

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 400
    assert "Unknown policy_type_id" in exc.value.detail


def test_resolve_taxonomy_rejects_mismatched_parent() -> None:
    """Sending insurance_type_id=2 with a policy_type_id whose parent is 1 must 400."""

    async def go():
        with patch.object(
            policy_service, "get_policy_type_with_category", new=AsyncMock()
        ) as get_pt:
            get_pt.return_value = {
                "id": 7,
                "name": "Comprehensive",
                "is_active": 1,
                "insurance_category_id": 1,
                "insurance_category_name": "Motor",
            }
            await policy_service._resolve_taxonomy(
                db=object(),
                policy_type_id=7,
                insurance_type_id=2,
                legacy_policy_type="auto",
            )

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 400
    assert "does not belong" in exc.value.detail


def test_resolve_taxonomy_legacy_path_returns_none_for_new_id() -> None:
    """Without ``policy_type_id`` we keep the new FK NULL — that's the Android contract."""

    async def go():
        with patch.object(
            policy_service, "resolve_insurance_type_id", new=AsyncMock()
        ) as legacy_slug, patch.object(
            policy_service, "get_policy_type_with_category", new=AsyncMock()
        ) as get_pt:
            legacy_slug.return_value = 42
            return await policy_service._resolve_taxonomy(
                db=object(),
                policy_type_id=None,
                insurance_type_id=None,
                legacy_policy_type="auto",
            ), get_pt

    (legacy_id, new_pt_id), get_pt = _run(go())
    assert legacy_id == 42
    assert new_pt_id is None
    get_pt.assert_not_awaited()  # new-FK path skipped


# --------------------------------------------------------------------------- #
# Validation in PATCH endpoints                                               #
# --------------------------------------------------------------------------- #


def test_update_contact_rejects_empty_patch() -> None:
    body = schemas.PolicyContactUpdate()  # no fields set

    async def go():
        await policy_service.update_contact(db=object(), user_id="u", policy_id=1, body=body)

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 400
    assert "No fields" in exc.value.detail


def test_update_contact_rejects_unknown_status() -> None:
    body = schemas.PolicyContactUpdate(contact_status="Wishful Thinking")

    async def go():
        await policy_service.update_contact(db=object(), user_id="u", policy_id=1, body=body)

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 400
    assert "contact_status must be one of" in exc.value.detail


def test_update_payment_rejects_unknown_label() -> None:
    body = schemas.PolicyPaymentUpdate(payment_status="MAGIC")

    async def go():
        await policy_service.update_payment(db=object(), user_id="u", policy_id=1, body=body)

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 400
    assert "payment_status must be one of" in exc.value.detail


def test_update_payment_rejects_non_pending_current_state() -> None:
    """The PATCH /payment workflow only fires from PENDING — anything else is a 400."""
    # Use a label inside ``ALLOWED_PAYMENT_UPDATE_FROM_PENDING`` so the
    # input-validation guard passes and the test actually exercises the
    # current-state check it was written to assert.
    body = schemas.PolicyPaymentUpdate(payment_status="CUSTOMER ONLINE")

    async def go():
        with patch.object(
            policy_service.policy_repo,
            "get_payment_status_label_for_user",
            new=AsyncMock(),
        ) as lookup:
            lookup.return_value = (True, "CUSTOMER ONLINE")
            await policy_service.update_payment(
                db=object(), user_id="u", policy_id=1, body=body
            )

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 400
    assert "PENDING" in exc.value.detail


def test_update_payment_404s_when_policy_not_found() -> None:
    body = schemas.PolicyPaymentUpdate(payment_status="CUSTOMER ONLINE")

    async def go():
        with patch.object(
            policy_service.policy_repo,
            "get_payment_status_label_for_user",
            new=AsyncMock(),
        ) as lookup:
            lookup.return_value = (False, None)
            await policy_service.update_payment(
                db=object(), user_id="u", policy_id=1, body=body
            )

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 404


def test_update_renewal_resolution_rejects_unknown_status() -> None:
    body = schemas.PolicyRenewalResolutionUpdate(renewal_status="Imaginary")

    async def go():
        await policy_service.update_renewal_resolution(
            db=object(), user_id="u", policy_id=1, body=body
        )

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 400
    assert "renewal_status must be one of" in exc.value.detail


# --------------------------------------------------------------------------- #
# Authorisation                                                               #
# --------------------------------------------------------------------------- #


def test_update_renewal_404s_when_policy_not_owned_by_user() -> None:
    body = schemas.PolicyRenewalResolutionUpdate(renewal_status="Open")

    async def go():
        with patch.object(
            policy_service.policy_repo, "policy_exists_for_user", new=AsyncMock()
        ) as exists:
            exists.return_value = False
            await policy_service.update_renewal_resolution(
                db=object(), user_id="u", policy_id=1, body=body
            )

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 404


def test_get_policy_404s_when_missing() -> None:
    async def go():
        with patch.object(
            policy_service.policy_repo,
            "fetch_policy_model_for_user",
            new=AsyncMock(),
        ) as fetch:
            fetch.return_value = (None, None)
            await policy_service.get_policy(db=object(), policy_id=1, user_id="u")

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 404


def test_create_policy_404s_when_customer_not_owned() -> None:
    payload = schemas.PolicyCreate(
        customer_id="42",
        policy_number="P/1",
        policy_type="Motor",
        start_date="2025-01-01",
        end_date="2026-01-01",
        premium=1.0,
    )

    async def go():
        with patch.object(
            policy_service.policy_repo, "customer_exists_for_user", new=AsyncMock()
        ) as exists:
            exists.return_value = False
            await policy_service.create_policy(db=object(), user_id="u", payload=payload)

    with pytest.raises(PolicyServiceError) as exc:
        _run(go())
    assert exc.value.status_code == 404
    assert "Customer not found" in exc.value.detail
