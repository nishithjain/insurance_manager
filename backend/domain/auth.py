"""
Auth domain primitives: roles, validators, and business invariants.

Framework-agnostic — no FastAPI, no aiosqlite. These constants and helpers encode
the *rules* of who can do what; the routers and services consume them.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class AppRole(str, Enum):
    """
    Role granted to an app_users row. Stored lowercase in the DB; the CHECK
    constraint in the schema enforces the same vocabulary.
    """

    ADMIN = "admin"
    USER = "user"

    @classmethod
    def parse(cls, value: str | None) -> "AppRole":
        normalized = (value or "").strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(
                f"Unknown role '{value}'. Allowed: {', '.join(r.value for r in cls)}"
            ) from exc


ALLOWED_ROLES: Final[frozenset[str]] = frozenset(r.value for r in AppRole)


def normalize_email(email: str | None) -> str:
    """
    Lowercase + strip. Email uniqueness in the DB is ``COLLATE NOCASE``, so we
    also store the canonical (lowercased) form to keep queries predictable.
    """
    if email is None:
        raise ValueError("email is required")
    cleaned = email.strip().lower()
    if not cleaned:
        raise ValueError("email is required")
    return cleaned
