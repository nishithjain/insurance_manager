"""
Tests for the expiry / renewal-window endpoints.

We deliberately seed policies whose ``end_date`` is computed relative to
``date.today()`` so the tests stay deterministic without having to mock the
clock — the only concession we make is to use windows wide enough that a
test running across midnight UTC still asserts on the right bucket.

What we cover:
- Policies expiring today land in the ``today`` summary bucket and the
  ``window=today`` listing with ``days_left == 0``.
- Policies expiring within N days are counted into the cumulative
  ``expiring_within_*_days`` summary fields.
- Expired policies (``end_date < today``) appear in ``window=expired`` and
  not in any future-window listing.
- ``days_left`` is calculated as ``end_date - today`` (signed integer).
- Contact status updates round-trip through the policy detail endpoint.
"""

from __future__ import annotations

from datetime import date, timedelta


def _today() -> str:
    return date.today().isoformat()


def _days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


# --------------------------------------------------------------------------- #
# Summary bucketing                                                            #
# --------------------------------------------------------------------------- #


def test_summary_buckets_count_today_and_future_windows(
    client, make_customer, make_policy
) -> None:
    cust = make_customer(name="Expiry Owner Bucket", phone="7100000001")
    p_today = make_policy(cust["id"], policy_number="POL-EXP-T", end_date=_today())
    p_5d = make_policy(cust["id"], policy_number="POL-EXP-5", end_date=_days(5))
    p_20d = make_policy(cust["id"], policy_number="POL-EXP-20", end_date=_days(20))

    body = client.get("/api/renewals/reminders").json()
    summary = body["summary"]
    assert summary["expiring_today"] >= 1
    # 5d <= 7d <= 15d <= 30d (cumulative) — each bucket includes earlier ones.
    assert summary["expiring_within_7_days"] >= 1
    assert summary["expiring_within_15_days"] >= 2
    assert summary["expiring_within_30_days"] >= 3

    # Sanity: the policies we just inserted exist as fetchable rows.
    for pid in (p_today["id"], p_5d["id"], p_20d["id"]):
        assert client.get(f"/api/policies/{pid}").status_code == 200


# --------------------------------------------------------------------------- #
# expiring-list endpoint                                                       #
# --------------------------------------------------------------------------- #


def test_expiring_list_today_window_has_zero_days_left(
    client, make_customer, make_policy
) -> None:
    cust = make_customer(name="Expiry Today Owner", phone="7100000002")
    p = make_policy(cust["id"], policy_number="POL-TODAY-001", end_date=_today())

    rows = client.get("/api/renewals/expiring-list", params={"window": "today"}).json()
    # The create endpoint returns ``id`` as a string (per the Policy schema)
    # whereas the renewal list returns it as an int — normalize before compare.
    pid = int(p["id"])
    target = next((r for r in rows if int(r["id"]) == pid), None)
    assert target is not None, "today policy missing from window=today"
    assert target["days_left"] == 0
    assert target["end_date"].startswith(_today())


def test_expiring_list_15_window_has_positive_days_left(
    client, make_customer, make_policy
) -> None:
    cust = make_customer(name="Expiry 10d Owner", phone="7100000003")
    p = make_policy(cust["id"], policy_number="POL-10D-001", end_date=_days(10))

    rows = client.get("/api/renewals/expiring-list", params={"window": "15"}).json()
    pid = int(p["id"])
    target = next((r for r in rows if int(r["id"]) == pid), None)
    assert target is not None
    assert 0 < target["days_left"] <= 15


def test_expiring_list_expired_window_excludes_future(
    client, make_customer, make_policy
) -> None:
    cust = make_customer(name="Expiry Expired Owner", phone="7100000004")
    expired = make_policy(
        cust["id"], policy_number="POL-EXPIRED-001", end_date=_days(-3)
    )
    future = make_policy(
        cust["id"], policy_number="POL-FUTURE-001", end_date=_days(20)
    )

    rows = client.get("/api/renewals/expiring-list", params={"window": "expired"}).json()
    ids = {int(r["id"]) for r in rows}
    assert int(expired["id"]) in ids
    assert int(future["id"]) not in ids
    target = next(r for r in rows if int(r["id"]) == int(expired["id"]))
    assert target["days_left"] < 0


def test_expiring_list_rejects_invalid_window(client) -> None:
    """The router constrains ``window`` via a pattern → FastAPI 422."""
    r = client.get("/api/renewals/expiring-list", params={"window": "bogus"})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# Contact status PATCH (covered briefly in the smoke test; here we focus on    #
# the read-back through the renewal listing where ``contact_status`` is        #
# surfaced via the policy row).                                                #
# --------------------------------------------------------------------------- #


def test_contact_status_round_trip(client, make_customer, make_policy) -> None:
    cust = make_customer(name="Contact Owner", phone="7100000005")
    p = make_policy(cust["id"], policy_number="POL-CONTACT-001", end_date=_days(10))

    r = client.patch(
        f"/api/policies/{p['id']}/contact",
        json={
            "contact_status": "Contacted Today",
            "last_contacted_at": _today(),
            "follow_up_date": _days(2),
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["contact_status"] == "Contacted Today"

    # Re-fetch the canonical policy row to confirm the patch persisted.
    after = client.get(f"/api/policies/{p['id']}").json()
    assert after["contact_status"] == "Contacted Today"


def test_contact_status_rejects_unknown_value(client, make_customer, make_policy) -> None:
    cust = make_customer(name="Contact Reject Owner", phone="7100000006")
    p = make_policy(cust["id"], policy_number="POL-CONTACT-002", end_date=_days(10))

    r = client.patch(
        f"/api/policies/{p['id']}/contact",
        json={"contact_status": "totally-bogus-status"},
    )
    assert r.status_code == 400
