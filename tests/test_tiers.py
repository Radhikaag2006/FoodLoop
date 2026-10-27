from datetime import date, timedelta

import pytest

from app.tiers import classify, escalate

TODAY = date(2026, 10, 20)


def test_expired_packaged_is_locked_to_recover():
    exp = TODAY - timedelta(days=1)
    r = classify("snacks", "fresh", exp, TODAY)
    assert r["tier"] == "D"
    assert set(r["locked"]) == {"B", "C"}
    assert r["allowed"] == ["D"]


def test_expired_flag_without_date_also_locks():
    r = classify("bakery", "fresh", None, TODAY, expired=True)
    assert r["tier"] == "D" and "C" in r["locked"]


def test_in_date_good_food_is_refused():
    """Good, in-date food has value: we are paid to take waste, so we
    do not take it (the old rescue tier is gone)."""
    for days in (0, 1, 30):
        with pytest.raises(ValueError, match="isn't waste"):
            classify("cooked", "fresh", TODAY + timedelta(days=days),
                     TODAY)
    with pytest.raises(ValueError):
        classify("vegetables", "fresh")            # no date, still good


def test_no_rescue_tier():
    from app.tiers import TIERS, TIER_ROUTES
    assert "A" not in TIERS and "A" not in TIER_ROUTES


def test_overripe_goes_to_process():
    r = classify("fruits", "overripe")
    assert r["tier"] == "B" and r["locked"] == []


def test_bruised_feed_only_if_feed_ok():
    assert classify("bakery", "bruised")["tier"] == "C"
    assert classify("dairy", "bruised")["tier"] == "D"


def test_spoiled_goes_to_recover():
    r = classify("vegetables", "spoiled")
    assert r["tier"] == "D" and set(r["locked"]) == {"B", "C"}


def test_fixed_items():
    assert classify("packaging")["tier"] == "E"
    assert classify("kitchen_waste")["tier"] == "D"


def test_feed_never_allowed_for_expired():
    r = classify("grains", "fresh", TODAY - timedelta(days=400), TODAY)
    assert "C" not in r["allowed"]


def test_escalate_skips_locked_tiers():
    assert escalate("B", []) == "C"
    assert escalate("B", ["C"]) == "D"
    assert escalate("C", []) == "D"
    assert escalate("D", []) == "D"


def test_bad_input():
    with pytest.raises(ValueError):
        classify("unicorn")
    with pytest.raises(ValueError):
        classify("bread", "weird")


def test_people_see_letters_a_to_d():
    from app.tiers import tier_letter, TIERS
    assert [tier_letter(k) for k in TIERS] == ["A", "B", "C", "D"]


def test_old_item_keys_still_work():
    """Lots saved before the category change keep their route."""
    from app.tiers import resolve
    assert resolve("tomato") == "vegetables" and resolve("bread") == "bakery"
    assert classify("banana", "overripe")["tier"] == "B"
    assert classify("tomato", "spoiled")["tier"] == "D"
