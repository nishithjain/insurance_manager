"""
Application-layer orchestration for policy create/read/update/delete.

The service consumes only repository functions plus pure schemas, never the
HTTP layer. The router (``backend/routers/policies.py``) reduces to a thin
wrapper that adapts ``HTTPException`` boundaries and the DI graph.

Why a service instead of putting everything in repositories:

* Several flows (create, update, contact PATCH, payment PATCH, renewal
  PATCH) share a "load → validate → write → commit → re-read" rhythm. The
  repetition lives here, once.
* Taxonomy resolution (legacy ``insurance_types`` FK + new ``policy_types``
  FK) is policy-creation business logic, not a single-table read, and so
  belongs above the repository layer.
* Authorisation ("does this policy belong to this user?") is enforced
  consistently — the router doesn't have to remember to scope every query.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import aiosqlite

from domain.constants import (
    ALLOWED_PAYMENT_UPDATE_FROM_PENDING,
    ALLOWED_POLICY_CONTACT_STATUSES,
    ALLOWED_RENEWAL_STATUSES,
    is_pending_payment_label,
)
from repositories import customer_repo, policy_detail_repo, policy_repo
from repositories.customer_repo import CUSTOMER_SELECT, customer_row_to_model
from repositories.insurance_type_repo import (
    get_policy_type_with_category,
    resolve_insurance_type_id,
    resolve_legacy_insurance_type_for_category,
)
from repositories.payment_status_repo import (
    default_payment_status_id,
    payment_status_id_by_name,
)
from schemas import (
    Policy,
    PolicyContactUpdate,
    PolicyCreate,
    PolicyDetailBundle,
    PolicyPaymentUpdate,
    PolicyRenewalResolutionUpdate,
    PolicyUpdate,
)


class PolicyServiceError(Exception):
    """
    Raised when a policy operation can't proceed but the failure is *expected*.

    The router translates this into a ``HTTPException`` with the status code
    pinned in :attr:`status_code`. We keep a project-local exception class so
    the application layer never imports FastAPI directly — that's the Clean
    Architecture rule the rest of this refactor is enforcing.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_customer_pk(customer_id: str) -> int:
    try:
        return int(customer_id)
    except (TypeError, ValueError):
        raise PolicyServiceError(404, "Customer not found")


async def _resolve_taxonomy(
    db: aiosqlite.Connection,
    *,
    policy_type_id: int | None,
    insurance_type_id: int | None,
    legacy_policy_type: str,
) -> tuple[int, int | None]:
    """
    Resolve both the legacy ``insurance_types`` FK and the new
    ``policy_types`` FK from the request body.

    Strategy (in priority order):
      1. ``policy_type_id`` (new) is present → look up its row and parent
         category. If ``insurance_type_id`` is also sent, verify the child
         belongs to that parent. Derive the legacy FK from the parent
         category's name.
      2. Otherwise fall back to the legacy slug-based resolver and leave
         ``policies.policy_type_id`` NULL (current Android contract).
    """
    if policy_type_id is not None:
        pt = await get_policy_type_with_category(db, int(policy_type_id))
        if not pt:
            raise PolicyServiceError(400, "Unknown policy_type_id")
        if (
            insurance_type_id is not None
            and int(insurance_type_id) != int(pt["insurance_category_id"])
        ):
            raise PolicyServiceError(
                400,
                "policy_type_id does not belong to the selected insurance_type_id",
            )
        legacy_id = await resolve_legacy_insurance_type_for_category(
            db, str(pt["insurance_category_name"])
        )
        return legacy_id, int(pt["id"])

    legacy_id = await resolve_insurance_type_id(db, legacy_policy_type)
    return legacy_id, None


# --------------------------------------------------------------------------- #
# Read flows                                                                  #
# --------------------------------------------------------------------------- #


async def list_policies(db: aiosqlite.Connection, user_id: str) -> list[Policy]:
    return await policy_repo.list_policy_models_for_user(db, user_id)


async def get_policy(
    db: aiosqlite.Connection, policy_id: int, user_id: str
) -> Policy:
    policy, _ = await policy_repo.fetch_policy_model_for_user(
        db, policy_id, user_id
    )
    if policy is None:
        raise PolicyServiceError(404, "Policy not found")
    return policy


async def get_policy_detail_bundle(
    db: aiosqlite.Connection, policy_id: int, user_id: str
) -> PolicyDetailBundle:
    policy, customer_pk = await policy_repo.fetch_policy_model_for_user(
        db, policy_id, user_id
    )
    if policy is None or customer_pk is None:
        raise PolicyServiceError(404, "Policy not found")

    async with db.execute(
        f"{CUSTOMER_SELECT} WHERE c.customer_id = ? AND c.user_id = ?",
        (customer_pk, user_id),
    ) as cur:
        customer_row = await cur.fetchone()
    if not customer_row:
        raise PolicyServiceError(404, "Customer not found")

    return PolicyDetailBundle(
        policy=policy,
        customer=customer_row_to_model(dict(customer_row)),
        category_group=await policy_detail_repo.get_category_group(db, policy_id),
        motor=await policy_detail_repo.load_motor_details(db, policy_id),
        health=await policy_detail_repo.load_health_details(db, policy_id),
        property_detail=await policy_detail_repo.load_property_details(
            db, policy_id
        ),
    )


# --------------------------------------------------------------------------- #
# Write flows                                                                 #
# --------------------------------------------------------------------------- #


async def create_policy(
    db: aiosqlite.Connection, user_id: str, payload: PolicyCreate
) -> Policy:
    customer_pk = _parse_customer_pk(payload.customer_id)
    if not await policy_repo.customer_exists_for_user(db, customer_pk, user_id):
        raise PolicyServiceError(404, "Customer not found")

    insurance_type_id, new_policy_type_id = await _resolve_taxonomy(
        db,
        policy_type_id=payload.policy_type_id,
        insurance_type_id=payload.insurance_type_id,
        legacy_policy_type=payload.policy_type,
    )
    payment_status_id = await default_payment_status_id(db)
    created_at = _now_iso()

    new_pid = await policy_repo.insert_policy(
        db,
        source_record_id=f"manual-{uuid.uuid4().hex}",
        customer_pk=customer_pk,
        insurance_type_id=insurance_type_id,
        policy_type_id=new_policy_type_id,
        premium=payload.premium,
        payment_status_id=payment_status_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        policy_number=payload.policy_number,
        status=payload.status,
        created_at=created_at,
    )
    await policy_repo.insert_empty_policy_detail(db, new_pid, insurance_type_id)
    await db.commit()

    policy = await policy_repo.fetch_policy_model(db, new_pid)
    if policy is None:
        # Defensive — if SELECT after insert returns nothing we have a deeper
        # problem than this endpoint can recover from.
        raise PolicyServiceError(500, "Policy created but could not be re-read")
    return policy


async def update_policy(
    db: aiosqlite.Connection,
    user_id: str,
    policy_id: int,
    payload: PolicyUpdate,
) -> Policy:
    if not await policy_repo.policy_exists_for_user(db, policy_id, user_id):
        raise PolicyServiceError(404, "Policy not found")

    customer_pk = _parse_customer_pk(payload.customer_id)
    if not await policy_repo.customer_exists_for_user(db, customer_pk, user_id):
        raise PolicyServiceError(404, "Customer not found")

    insurance_type_id, new_policy_type_id = await _resolve_taxonomy(
        db,
        policy_type_id=payload.policy_type_id,
        insurance_type_id=payload.insurance_type_id,
        legacy_policy_type=payload.policy_type,
    )
    payment_status_id = await default_payment_status_id(db)
    now = _now_iso()

    await policy_repo.update_policy_core(
        db,
        policy_id,
        customer_pk=customer_pk,
        insurance_type_id=insurance_type_id,
        policy_type_id=new_policy_type_id,
        # Only overwrite the new FK when the client actually sent one — keeps
        # legacy clients (Android) from clobbering a previously-set value.
        overwrite_policy_type_id=payload.policy_type_id is not None,
        policy_number=payload.policy_number,
        premium=payload.premium,
        payment_status_id=payment_status_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        now=now,
    )

    if payload.customer is not None:
        # Only fields explicitly provided by the client are touched (PATCH-like).
        # ``full_name`` is unreachable from this body by design — see
        # :class:`PolicyUpdateCustomerFields`.
        cust_patch = payload.customer.model_dump(exclude_unset=True)
        await customer_repo.update_customer_contact_fields(
            db, customer_pk, cust_patch, now
        )
        if "address" in cust_patch:
            await customer_repo.upsert_customer_address(
                db, customer_pk, cust_patch["address"], now
            )

    await db.commit()
    policy = await policy_repo.fetch_policy_model(db, policy_id)
    if policy is None:
        raise PolicyServiceError(500, "Policy updated but could not be re-read")
    return policy


async def update_contact(
    db: aiosqlite.Connection,
    user_id: str,
    policy_id: int,
    body: PolicyContactUpdate,
) -> Policy:
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise PolicyServiceError(400, "No fields to update")

    new_status = patch.get("contact_status")
    if new_status is not None and new_status not in ALLOWED_POLICY_CONTACT_STATUSES:
        raise PolicyServiceError(
            400,
            f"contact_status must be one of: {sorted(ALLOWED_POLICY_CONTACT_STATUSES)}",
        )

    if not await policy_repo.policy_exists_for_user(db, policy_id, user_id):
        raise PolicyServiceError(404, "Policy not found")

    await policy_repo.update_policy_contact_fields(
        db, policy_id, patch, _now_iso()
    )
    await db.commit()
    policy = await policy_repo.fetch_policy_model(db, policy_id)
    if policy is None:
        raise PolicyServiceError(500, "Policy updated but could not be re-read")
    return policy


async def update_payment(
    db: aiosqlite.Connection,
    user_id: str,
    policy_id: int,
    body: PolicyPaymentUpdate,
) -> Policy:
    new_label = (body.payment_status or "").strip()
    if new_label not in ALLOWED_PAYMENT_UPDATE_FROM_PENDING:
        raise PolicyServiceError(
            400,
            f"payment_status must be one of: {sorted(ALLOWED_PAYMENT_UPDATE_FROM_PENDING)}",
        )

    found, current_label = await policy_repo.get_payment_status_label_for_user(
        db, policy_id, user_id
    )
    if not found:
        raise PolicyServiceError(404, "Policy not found")
    if not is_pending_payment_label(current_label):
        raise PolicyServiceError(
            400, "Payment can only be updated from PENDING in this workflow."
        )

    note = (body.payment_note or "").strip() or None
    now = _now_iso()

    new_status_id = await payment_status_id_by_name(db, new_label)
    if new_status_id is None:
        # Auto-create the label when missing — matches prior behavior so
        # callers don't need to manually seed every variant.
        await db.execute(
            "INSERT INTO payment_statuses (status_name) VALUES (?)",
            (new_label,),
        )
        new_status_id = await payment_status_id_by_name(db, new_label)

    await policy_repo.update_policy_payment(
        db,
        policy_id,
        payment_status_id=int(new_status_id),  # type: ignore[arg-type]
        note=note,
        now=now,
    )
    await db.commit()
    policy = await policy_repo.fetch_policy_model(db, policy_id)
    if policy is None:
        raise PolicyServiceError(500, "Policy updated but could not be re-read")
    return policy


async def update_renewal_resolution(
    db: aiosqlite.Connection,
    user_id: str,
    policy_id: int,
    body: PolicyRenewalResolutionUpdate,
) -> Policy:
    if body.renewal_status not in ALLOWED_RENEWAL_STATUSES:
        raise PolicyServiceError(
            400,
            f"renewal_status must be one of: {sorted(ALLOWED_RENEWAL_STATUSES)}",
        )

    if not await policy_repo.policy_exists_for_user(db, policy_id, user_id):
        raise PolicyServiceError(404, "Policy not found")

    note = (body.renewal_resolution_note or "").strip() or None
    await policy_repo.update_policy_renewal_resolution(
        db,
        policy_id,
        status=body.renewal_status,
        note=note,
        now=_now_iso(),
        resolved_by=user_id,
    )
    await db.commit()
    policy = await policy_repo.fetch_policy_model(db, policy_id)
    if policy is None:
        raise PolicyServiceError(500, "Policy updated but could not be re-read")
    return policy


async def delete_policy(
    db: aiosqlite.Connection, user_id: str, policy_id: int
) -> dict:
    await policy_repo.delete_policy_for_user(db, policy_id, user_id)
    await db.commit()
    return {"message": "Policy deleted successfully"}
