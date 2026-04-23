"""
Domain constants: allowed enum-ish values, canonical labels, and lookup tables.

Previously scattered across ``server.py``. Centralizing them prevents the "magic
string" problem where ``"PENDING"`` or ``"Open"`` is spelled differently by different
handlers.
"""

from __future__ import annotations

from typing import Final


# ---- Renewal resolution ------------------------------------------------------

ALLOWED_RENEWAL_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "Open",
        "RenewedWithUs",
        "RenewedElsewhere",
        "NotInterested",
        "PolicyClosed",
        "Duplicate",
    }
)


# ---- Renewal contact tracking -----------------------------------------------

ALLOWED_POLICY_CONTACT_STATUSES: Final[frozenset[str]] = frozenset(
    {"Not Contacted", "Contacted Today", "Follow-up Needed"}
)


# ---- Payment workflow -------------------------------------------------------

PENDING_PAYMENT_STATUS_NAME: Final[str] = "PENDING"

# Allowed targets when moving off PENDING — extend with new labels in DB + frontend paymentStatus.js.
ALLOWED_PAYMENT_UPDATE_FROM_PENDING: Final[frozenset[str]] = frozenset(
    {
        "CUSTOMER ONLINE",
        "CUSTOMER CHEQUE",
        "TRANSFER TO SAMRAJ",
        "CASH TO SAMRAJ",
        "CASH TO SANDESH",
    }
)


def is_pending_payment_label(name: str | None) -> bool:
    """Case-insensitive / whitespace-tolerant check for the PENDING label."""
    return (name or "").strip().upper() == PENDING_PAYMENT_STATUS_NAME


# ---- Manual policy form -----------------------------------------------------

# Manual policy form slugs → insurance_types.insurance_type_name
POLICY_SLUG_TO_TYPE_NAME: Final[dict[str, str]] = {
    "auto": "Private Car",
    "health": "Health",
    "home": "Property",
    "business": "Property",
    "life": "Health",
}


# ---- Upload limits ----------------------------------------------------------

STATEMENT_CSV_MAX_BYTES: Final[int] = 15 * 1024 * 1024
