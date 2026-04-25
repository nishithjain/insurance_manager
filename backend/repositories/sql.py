"""
Backwards-compatible re-export shim for the old ``repositories.sql`` module.

The contents were split into focused modules during the Clean Architecture
refactor:

* :mod:`repositories.customer_repo` — customer SELECT shapes + row mappers
* :mod:`repositories.policy_repo` — policy SELECT shapes + row mapper +
  per-LOB stub-row inserter
* :mod:`repositories.insurance_type_repo` — taxonomy lookups (legacy +
  new ``insurance_categories`` / ``policy_types`` tables)
* :mod:`repositories.payment_status_repo` — payment-status lookups
* :mod:`repositories._helpers` — generic id parsing and numeric coercion

Every public symbol previously importable as ``from repositories.sql import X``
is re-exported here so router imports keep working unchanged. New code should
import from the focused module directly.
"""

from __future__ import annotations

from ._helpers import maybe_int, parse_customer_id, parse_policy_id, sql_float
from .customer_repo import (
    CUSTOMER_ADMIN_SELECT,
    CUSTOMER_SELECT,
    customer_admin_row_to_model,
    customer_row_to_model,
)
from .insurance_type_repo import (
    get_insurance_category_id_by_name,
    get_policy_type_with_category,
    resolve_insurance_type_id,
    resolve_legacy_insurance_type_for_category,
)
from .payment_status_repo import (
    default_payment_status_id,
    payment_status_id_by_name,
)
from .policy_repo import (
    EXPORT_POLICY_SELECT,
    POLICY_SELECT,
    insert_empty_policy_detail,
    policy_row_to_model,
)

__all__ = [
    "CUSTOMER_ADMIN_SELECT",
    "CUSTOMER_SELECT",
    "EXPORT_POLICY_SELECT",
    "POLICY_SELECT",
    "customer_admin_row_to_model",
    "customer_row_to_model",
    "default_payment_status_id",
    "get_insurance_category_id_by_name",
    "get_policy_type_with_category",
    "insert_empty_policy_detail",
    "maybe_int",
    "parse_customer_id",
    "parse_policy_id",
    "payment_status_id_by_name",
    "policy_row_to_model",
    "resolve_insurance_type_id",
    "resolve_legacy_insurance_type_for_category",
    "sql_float",
]
