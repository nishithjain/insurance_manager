"""
Admin-facing payloads for the "Insurance Master" CRUD page.

The public read-only :class:`InsuranceTypeOut` / :class:`PolicyTypeOut` in
``schemas/policy.py`` are deliberately minimal (they feed cascading dropdowns
on the policy form). The admin grid needs more — description text,
audit timestamps, and a flag indicating whether the row is currently in use
by a policy. Keeping these in their own module avoids inflating the
hot-path policy schemas.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
# Insurance Type (parent)                                                     #
# --------------------------------------------------------------------------- #


class InsuranceTypeAdminOut(BaseModel):
    """Full row + usage counters returned by the admin Insurance Type APIs."""

    id: int
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    in_use: bool = False
    policy_type_count: int = 0


class InsuranceTypeCreate(BaseModel):
    """POST payload — only ``name`` is required."""

    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Insurance Type name is required.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class InsuranceTypeUpdate(BaseModel):
    """PUT payload — every field is optional so admins can patch one at a time."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Insurance Type name cannot be blank.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


# --------------------------------------------------------------------------- #
# Policy Type (child)                                                         #
# --------------------------------------------------------------------------- #


class PolicyTypeAdminOut(BaseModel):
    """Full row + parent name + usage flag for the admin Policy Type grid."""

    id: int
    insurance_type_id: int
    insurance_type_name: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    in_use: bool = False


class PolicyTypeCreate(BaseModel):
    """POST payload — both parent FK and ``name`` are required."""

    insurance_type_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Policy Type name is required.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class PolicyTypeUpdate(BaseModel):
    """PUT payload — every field is optional."""

    insurance_type_id: Optional[int] = Field(default=None, ge=1)
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Policy Type name cannot be blank.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


__all__ = [
    "InsuranceTypeAdminOut",
    "InsuranceTypeCreate",
    "InsuranceTypeUpdate",
    "PolicyTypeAdminOut",
    "PolicyTypeCreate",
    "PolicyTypeUpdate",
]
