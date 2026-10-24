from datetime import date, timedelta

import pytest

from app.tiers import classify, escalate

TODAY = date(2026, 10, 20)


def test_expired_packaged_is_locked_to_recover():
    exp = TODAY - timedelta(days=1)
    r = classify("biscuits", "fresh", exp, TODAY)
    assert r["tier"] == "D"
    assert set(r["locked"]) == {"A", "B", "C"}
    assert r["allowed"] == ["D"]


def test_expired_flag_without_date_also_locks():
    r = classify("bread", "fresh", None, TODAY, expired=True)
    assert r["tier"] == "D" and "C" in r["locked"]


def test_within_date_is_rescue_with_urgency():
    near = classify("ready_pack", "fresh", TODAY + timedelta(days=1),
                    TODAY)
    far = classify("ready_pack", "fresh", TODAY + timedelta(days=30),
                   TODAY)
    assert near["tier"] == "A" and near["urgency"] == "high"
    assert far["tier"] == "A" and far["urgency"] == "low"


def test_expires_today_is_still_rescue():
    r = classify("dairy", "fresh", TODAY, TODAY)
    assert r["tier"] == "A" and r["urgency"] == "high"


def test_overripe_goes_to_process():
    r = classify("banana", "overripe")
    assert r["tier"] == "B" and r["locked"] == ["A"]


def test_bruised_feed_only_if_feed_ok():
    assert classify("bread", "bruised")["tier"] == "C"
    assert classify("dairy", "bruised")["tier"] == "D"


def test_spoiled_goes_to_recover():
    r = classify("tomato", "spoiled")
    assert r["tier"] == "D" and set(r["locked"]) == {"A", "B", "C"}


def test_fixed_items():
    assert classify("packaging")["tier"] == "E"
    assert classify("kitchen_waste")["tier"] == "D"


def test_feed_never_allowed_for_expired():
    r = classify("grains", "fresh", TODAY - timedelta(days=400), TODAY)
    assert "C" not in r["allowed"]


def test_escalate_skips_locked_tiers():
    assert escalate("A", []) == "B"
    assert escalate("A", ["B"]) == "C"
    assert escalate("A", ["B", "C"]) == "D"
    assert escalate("D", []) == "D"


def test_bad_input():
    with pytest.raises(ValueError):
        classify("unicorn")
    with pytest.raises(ValueError):
        classify("bread", "weird")
