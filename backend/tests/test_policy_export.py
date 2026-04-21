"""Unit tests for policy CSV export mapping."""
import json

from policy_export import (
    build_export_row,
    normalize_export_category,
    compute_primary_details,
    RawDetailSnapshot,
)


def _minimal_row(**kwargs):
    base = {
        "policy_id": 1,
        "source_record_id": "s1",
        "customer_name": "Test User",
        "customer_email": "t@example.com",
        "customer_phone": "999",
        "customer_address": "Addr",
        "policy_number": "POL1",
        "policy_type": "Private Car",
        "coverage_category": "Motor",
        "insurer_company": "Acme Ins",
        "ncb_discount": "",
        "payment_status_name": "Paid",
        "agent_name": "",
        "card_details": "",
        "start_date": "2025-01-01",
        "end_date": "2026-01-01",
        "created_at": "",
        "updated_at": "",
        "premium": 1000,
        "status": "active",
        "motor_vehicle_no": "KA01AB1234",
        "motor_vehicle_details": "CAR",
        "motor_idv": 500000,
        "motor_engine_no": "E1",
        "motor_chassis_no": "C1",
        "motor_od_premium": 800,
        "motor_tp_premium": 200,
        "health_plan_name": None,
        "health_sum_insured": None,
        "health_cover_type": None,
        "health_members_covered": None,
        "health_base_premium": None,
        "health_additional_premium": None,
        "property_product_name": None,
        "property_sum_insured": None,
        "property_sub_product": None,
        "property_risk_location": None,
        "property_base_premium": None,
        "property_additional_premium": None,
    }
    base.update(kwargs)
    return base


def test_normalize_category():
    assert normalize_export_category("Motor") == "Motor"
    assert normalize_export_category("Health") == "Health"
    assert normalize_export_category("Property") == "Non-Motor"
    assert normalize_export_category("") == "Unknown"


def test_motor_primary_prefers_vehicle_no():
    notes = []
    s = RawDetailSnapshot(motor_vehicle_no="MH12AB1234", motor_vehicle_details="Sedan")
    assert compute_primary_details("Motor", s, notes) == "MH12AB1234"


def test_health_primary_plan_not_motor_registration():
    notes = []
    s = RawDetailSnapshot(
        health_plan_name="Family Floater 5L",
        motor_vehicle_no="Should not appear in primary for Health",
    )
    assert compute_primary_details("Health", s, notes) == "Family Floater 5L"


def test_export_row_motor_has_no_health_in_primary():
    row = _minimal_row(coverage_category="Motor")
    er = build_export_row(row)
    assert er.cells[5] == "KA01AB1234"  # primary_details column index
    extra = json.loads(er.cells[11])
    assert extra["motor"]["vehicle_no"] == "KA01AB1234"
    assert extra["health"]["plan_name"] is None


def test_export_health_legacy_motor_in_extra_not_in_primary():
    row = _minimal_row(
        coverage_category="Health",
        motor_vehicle_no="OPTIM",
        motor_vehicle_details="Family",
        motor_idv=500000,
        motor_engine_no="IND",
        motor_chassis_no="2A + 2C",
        motor_od_premium=100,
        motor_tp_premium=50,
        health_plan_name=None,
    )
    er = build_export_row(row)
    extra = json.loads(er.cells[11])
    assert "inferred_health_from_motor_legacy" in extra
    assert extra["motor"]["vehicle_no"] == "OPTIM"
    pd = er.cells[5]
    assert "OPTIM" in pd or "Family" in pd
