"""
Policy CSV export — slim business-facing columns + JSON ``extra_details`` for full fidelity.

Mapping is driven by ``insurance_types.category_group`` (Motor / Health / everything else → Non-Motor),
not by column order. Raw detail rows are preserved under ``motor`` / ``health`` / ``property`` in
``extra_details`` so nothing is dropped when legacy imports stored data in the “wrong” table.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# --- Public CSV layout (single business-friendly row) ---------------------------------

EXPORT_POLICIES_CSV_HEADERS: List[str] = [
    "customer_name",
    "address",
    "phone_number",
    "policy_type",
    "category",
    "primary_details",
    "company",
    "policy_number",
    "premium",
    "policy_end_date",
    "payment_status",
    "extra_details",
]

# Keys from the exporter SQL row that are surfaced in the 12 columns (rest → policy_extras / JSON).
_SLIM_DIRECT_KEYS = frozenset(
    {
        "customer_name",
        "customer_address",
        "customer_phone",
        "policy_type",
        "policy_number",
        "insurer_company",
        "premium",
        "end_date",
        "payment_status_name",
    }
)


def _str_val(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _num_cell(v: Any) -> Any:
    if v is None:
        return ""
    try:
        return float(v)
    except (TypeError, ValueError):
        s = str(v).strip()
        return s if s else ""


def _json_safe(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return str(v)


_IN_VEHICLE_REG = re.compile(
    r"^[A-Z]{2}[0-9]{2}[A-Z]{0,3}[0-9]{4}$|^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$",
    re.IGNORECASE,
)


def _looks_like_vehicle_registration(s: str) -> bool:
    t = s.replace(" ", "").upper()
    if len(t) < 8:
        return False
    return bool(_IN_VEHICLE_REG.match(t))


_HEALTHISH_TOKENS = re.compile(
    r"\b(HEALTH|FLOATER|BOOSTER|BASE|TOPUP|OPTIM|FAMILY|INDIVIDUAL|"
    r"MEDICLAIM|CORONA|ACTIVATE|ELEVATE|GHI|PA\s*POLICY)\b",
    re.IGNORECASE,
)


def _looks_healthish_text(s: str) -> bool:
    if not s or len(s) < 3:
        return False
    if _HEALTHISH_TOKENS.search(s):
        return True
    if re.search(r"\d+\s*[A-Z]\s*\+", s):
        return True
    return False


@dataclass
class RawDetailSnapshot:
    """Columns from exporter SQL (aliases match ``_EXPORT_POLICY_SELECT``)."""

    motor_vehicle_no: Optional[str] = None
    motor_vehicle_details: Optional[str] = None
    motor_idv: Any = None
    motor_engine_no: Optional[str] = None
    motor_chassis_no: Optional[str] = None
    motor_od_premium: Any = None
    motor_tp_premium: Any = None
    health_plan_name: Optional[str] = None
    health_sum_insured: Any = None
    health_cover_type: Optional[str] = None
    health_members_covered: Optional[str] = None
    health_base_premium: Any = None
    health_additional_premium: Any = None
    property_product_name: Optional[str] = None
    property_sum_insured: Any = None
    property_sub_product: Optional[str] = None
    property_risk_location: Optional[str] = None
    property_base_premium: Any = None
    property_additional_premium: Any = None


def _snapshot_from_row(r: Dict[str, Any]) -> RawDetailSnapshot:
    return RawDetailSnapshot(
        motor_vehicle_no=r.get("motor_vehicle_no"),
        motor_vehicle_details=r.get("motor_vehicle_details"),
        motor_idv=r.get("motor_idv"),
        motor_engine_no=r.get("motor_engine_no"),
        motor_chassis_no=r.get("motor_chassis_no"),
        motor_od_premium=r.get("motor_od_premium"),
        motor_tp_premium=r.get("motor_tp_premium"),
        health_plan_name=r.get("health_plan_name"),
        health_sum_insured=r.get("health_sum_insured"),
        health_cover_type=r.get("health_cover_type"),
        health_members_covered=r.get("health_members_covered"),
        health_base_premium=r.get("health_base_premium"),
        health_additional_premium=r.get("health_additional_premium"),
        property_product_name=r.get("property_product_name"),
        property_sum_insured=r.get("property_sum_insured"),
        property_sub_product=r.get("property_sub_product"),
        property_risk_location=r.get("property_risk_location"),
        property_base_premium=r.get("property_base_premium"),
        property_additional_premium=r.get("property_additional_premium"),
    )


def _motor_native_dict(s: RawDetailSnapshot) -> Dict[str, Any]:
    return {
        "vehicle_no": _json_safe(s.motor_vehicle_no),
        "vehicle_details": _json_safe(s.motor_vehicle_details),
        "idv_of_vehicle": _num_cell(s.motor_idv) if s.motor_idv not in (None, "") else None,
        "engine_no": _json_safe(s.motor_engine_no),
        "chassis_no": _json_safe(s.motor_chassis_no),
        "od_premium": _num_cell(s.motor_od_premium) if s.motor_od_premium not in (None, "") else None,
        "tp_premium": _num_cell(s.motor_tp_premium) if s.motor_tp_premium not in (None, "") else None,
    }


def _health_native_dict(s: RawDetailSnapshot) -> Dict[str, Any]:
    return {
        "plan_name": _json_safe(s.health_plan_name),
        "sum_insured": _num_cell(s.health_sum_insured) if s.health_sum_insured not in (None, "") else None,
        "cover_type": _json_safe(s.health_cover_type),
        "members_covered": _json_safe(s.health_members_covered),
        "base_premium": _num_cell(s.health_base_premium) if s.health_base_premium not in (None, "") else None,
        "additional_premium": _num_cell(s.health_additional_premium)
        if s.health_additional_premium not in (None, "")
        else None,
    }


def _property_native_dict(s: RawDetailSnapshot) -> Dict[str, Any]:
    return {
        "product_name": _json_safe(s.property_product_name),
        "sum_insured": _num_cell(s.property_sum_insured) if s.property_sum_insured not in (None, "") else None,
        "sub_product": _json_safe(s.property_sub_product),
        "risk_location": _json_safe(s.property_risk_location),
        "base_premium": _num_cell(s.property_base_premium) if s.property_base_premium not in (None, "") else None,
        "additional_premium": _num_cell(s.property_additional_premium)
        if s.property_additional_premium not in (None, "")
        else None,
    }


def _any_value(d: Dict[str, Any]) -> bool:
    for v in d.values():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if v == "":
            continue
        return True
    return False


def _remap_motor_to_health_semantics(s: RawDetailSnapshot) -> Dict[str, Any]:
    """Legacy statement import stored health lines in motor_policy_details."""
    reg = _str_val(s.motor_vehicle_no)
    det = _str_val(s.motor_vehicle_details)
    parts = [p for p in (reg, det) if p and p.upper() != "HEALTH"]
    plan = " · ".join(parts) if parts else (det or reg or "")
    return {
        "plan_name": plan or None,
        "sum_insured": _num_cell(s.motor_idv) if s.motor_idv not in (None, "") else None,
        "cover_type": _json_safe(s.motor_engine_no),
        "members_covered": _json_safe(s.motor_chassis_no),
        "base_premium": _num_cell(s.motor_od_premium) if s.motor_od_premium not in (None, "") else None,
        "additional_premium": _num_cell(s.motor_tp_premium)
        if s.motor_tp_premium not in (None, "")
        else None,
    }


def normalize_export_category(raw: Any) -> str:
    """
    CSV ``category`` column: Motor | Health | Non-Motor | Unknown.
    DB ``category_group`` values outside Motor/Health are exported as Non-Motor (e.g. Property, Fire).
    """
    s = _str_val(raw)
    if not s:
        return "Unknown"
    if s == "Motor":
        return "Motor"
    if s == "Health":
        return "Health"
    if s == "Unknown":
        return "Unknown"
    return "Non-Motor"


def export_file_bucket(category: str) -> str:
    """Which split file a row belongs to: motor | health | non_motor."""
    if category == "Motor":
        return "motor"
    if category == "Health":
        return "health"
    return "non_motor"


def _primary_motor(s: RawDetailSnapshot) -> str:
    vn = _str_val(s.motor_vehicle_no)
    vd = _str_val(s.motor_vehicle_details)
    return vn or vd


def _primary_health(s: RawDetailSnapshot, notes: List[str]) -> Tuple[str, bool]:
    """
    Returns (primary_text, used_legacy_remap).
    Health primary is ``plan_name``; if the health row is empty, reconstruct from motor (legacy).
    """
    plan = _str_val(s.health_plan_name)
    if plan:
        return plan, False
    hnat = _health_native_dict(s)
    if _any_value({k: v for k, v in hnat.items() if k != "plan_name"}):
        notes.append("health: plan_name empty but other health_* columns present — primary_details left blank")
        return "", False
    md = _motor_native_dict(s)
    if _any_value(md):
        rem = _remap_motor_to_health_semantics(s)
        pn = _str_val(rem.get("plan_name"))
        notes.append(
            "legacy: health plan text derived from motor_policy_details (statement import); "
            "raw motor bytes kept in extra_details.motor"
        )
        return pn, True
    return "", False


def _primary_non_motor(s: RawDetailSnapshot) -> str:
    return _str_val(s.property_product_name)


def compute_primary_details(category: str, s: RawDetailSnapshot, notes: List[str]) -> str:
    if category == "Motor":
        return _primary_motor(s)
    if category == "Health":
        text, _ = _primary_health(s, notes)
        return text
    if category in ("Non-Motor", "Unknown"):
        if category == "Unknown":
            # Prefer non-motor product, then motor id, then health plan — explicit, not positional CSV.
            pm = _primary_non_motor(s)
            if pm:
                return pm
            mot = _primary_motor(s)
            if mot:
                notes.append(
                    "unknown_category: primary_details used motor vehicle fields (no property product); "
                    "see extra_details for full breakdown"
                )
                return mot
            hp, _ = _primary_health(s, notes)
            return hp
        return _primary_non_motor(s)
    return ""


def _policy_extras_from_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """Everything not represented in the slim columns or detail JSON subtrees."""
    out: Dict[str, Any] = {}
    for k, v in r.items():
        if k in _SLIM_DIRECT_KEYS:
            continue
        if k == "coverage_category":
            continue
        if k.startswith("motor_") or k.startswith("health_") or k.startswith("property_"):
            continue
        out[k] = _json_safe(v)
    return out


def build_extra_details_json(
    r: Dict[str, Any],
    category: str,
    snap: RawDetailSnapshot,
    validation_notes: List[str],
) -> str:
    """
    Structured JSON: raw motor/health/property dicts (DB-faithful names) + policy_extras + notes.
    Never merges health into motor keys — tables are separate; legacy overlap is described in notes.
    """
    motor = _motor_native_dict(snap)
    health = _health_native_dict(snap)
    prop = _property_native_dict(snap)

    payload: Dict[str, Any] = {
        "motor": motor,
        "health": health,
        "property": prop,
        "policy_extras": _policy_extras_from_row(r),
        "validation_notes": list(validation_notes),
        "source_category_group": _str_val(r.get("coverage_category")) or None,
    }
    # Readable reconstruction of health semantics when statement import only filled motor_* .
    if category == "Health" and (not _any_value(health)) and _any_value(motor):
        payload["inferred_health_from_motor_legacy"] = _remap_motor_to_health_semantics(snap)

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


@dataclass
class ExportRowResult:
    cells: List[Any]
    coverage_category: str
    export_bucket: str
    notes: List[str] = field(default_factory=list)
    suspicious: bool = False


def _validate_and_note(
    category: str,
    snap: RawDetailSnapshot,
    primary_details: str,
    notes: List[str],
) -> bool:
    """
    Cross-family checks. Does not remove data — only records notes / suspicious flag.
    """
    suspicious = False
    motor_d = _motor_native_dict(snap)
    health_d = _health_native_dict(snap)
    prop_d = _property_native_dict(snap)
    motor_populated = _any_value(motor_d)
    health_populated = _any_value(health_d)
    prop_populated = _any_value(prop_d)

    if category == "Motor":
        if health_populated:
            notes.append(
                "validation: health_policy_details has values while category is Motor — "
                "see extra_details.health (not copied into primary_details)"
            )
        if prop_populated:
            notes.append(
                "validation: property_policy_details has values while category is Motor — "
                "see extra_details.property"
            )
        pd = _str_val(primary_details)
        if pd and _looks_healthish_text(pd) and not _looks_like_vehicle_registration(pd):
            notes.append(
                "validation: primary_details looks like health vocabulary on a Motor row — "
                "verify insurance type classification"
            )
            suspicious = True

    elif category == "Health":
        if motor_populated:
            notes.append(
                "validation: motor_policy_details has values while category is Health — "
                "often legacy statement import; see extra_details.motor"
            )
        if prop_populated:
            notes.append(
                "validation: property_policy_details has values while category is Health — "
                "see extra_details.property"
            )
        pd = _str_val(primary_details)
        if pd and _looks_like_vehicle_registration(pd):
            notes.append(
                "validation: primary_details looks like a vehicle number on a Health row — "
                "verify data / classification"
            )
            suspicious = True

    elif category == "Non-Motor":
        if motor_populated:
            notes.append(
                "validation: motor_policy_details has values while category is Non-Motor — "
                "see extra_details.motor"
            )
        if health_populated:
            notes.append(
                "validation: health_policy_details has values while category is Non-Motor — "
                "see extra_details.health"
            )

    elif category == "Unknown":
        notes.append(
            "validation: insurance category_group is Unknown — primary_details heuristic may mix sources; "
            "see extra_details and source_category_group"
        )

    return suspicious


def build_export_row(r: Dict[str, Any]) -> ExportRowResult:
    """Build one CSV row from a joined policy dict (see ``_EXPORT_POLICY_SELECT``)."""
    notes: List[str] = []
    snap = _snapshot_from_row(r)
    raw_cat = r.get("coverage_category")
    category = normalize_export_category(raw_cat)
    bucket = export_file_bucket(category)

    primary = compute_primary_details(category, snap, notes)
    suspicious = _validate_and_note(category, snap, primary, notes)

    extra_json = build_extra_details_json(r, category, snap, notes)

    row_out = {
        "customer_name": _str_val(r.get("customer_name")),
        "address": _str_val(r.get("customer_address")),
        "phone_number": _str_val(r.get("customer_phone")),
        "policy_type": _str_val(r.get("policy_type")),
        "category": category,
        "primary_details": primary,
        "company": _str_val(r.get("insurer_company")),
        "policy_number": _str_val(r.get("policy_number")),
        "premium": _num_cell(r.get("premium")),
        "policy_end_date": _str_val(r.get("end_date")),
        "payment_status": _str_val(r.get("payment_status_name")),
        "extra_details": extra_json,
    }

    cells = [row_out.get(h, "") for h in EXPORT_POLICIES_CSV_HEADERS]

    return ExportRowResult(
        cells=cells,
        coverage_category=category,
        export_bucket=bucket,
        notes=notes,
        suspicious=suspicious,
    )


def validate_and_summarize_export(
    results: List[ExportRowResult], policy_ids: Optional[List[Any]] = None
) -> Dict[str, Any]:
    motor_n = sum(1 for r in results if r.export_bucket == "motor")
    health_n = sum(1 for r in results if r.export_bucket == "health")
    non_motor_n = sum(1 for r in results if r.export_bucket == "non_motor")
    susp_idx = [i for i, r in enumerate(results) if r.suspicious]

    summary = {
        "total_rows": len(results),
        "motor_rows": motor_n,
        "health_rows": health_n,
        "non_motor_rows": non_motor_n,
        "suspicious_row_count": len(susp_idx),
    }

    logger.info(
        "policy CSV export validation: total=%s motor=%s health=%s non_motor=%s suspicious=%s",
        summary["total_rows"],
        summary["motor_rows"],
        summary["health_rows"],
        summary["non_motor_rows"],
        summary["suspicious_row_count"],
    )

    for idx in susp_idx[:5]:
        res = results[idx]
        pid = policy_ids[idx] if policy_ids and idx < len(policy_ids) else "?"
        logger.warning(
            "export flagged sample [policy_id=%s]: category=%s notes=%s",
            pid,
            res.coverage_category,
            "; ".join(res.notes)[:500],
        )

    return summary


def render_split_csv_rows(results: List[ExportRowResult], bucket: str) -> List[List[Any]]:
    """Rows for motor_export / health_export / non_motor (same headers)."""
    return [r.cells for r in results if r.export_bucket == bucket]
