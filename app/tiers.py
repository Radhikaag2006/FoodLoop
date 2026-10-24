"""Rule engine: expiry date + condition + item decides the route.

Key rule: once food is expired (or spoiled) the human-food tiers
A (rescue), B (process) and C (feed) are LOCKED. Expired food can only
go to certified compost / anaerobic digestion (D). Feed (C) is only for
non-expired surplus. Confirm the legal details with FSSAI before use.
"""
from datetime import date

TIERS = {
    "A": "Rescue",
    "B": "Process",
    "C": "Feed",
    "D": "Recover",
    "E": "Packaging",
}

TIER_ROUTES = {
    "A": "Discount sale, NGOs, community kitchens",
    "B": "Pulp, jam, pickle, dehydration units",
    "C": "Animal feed makers (non-expired surplus only)",
    "D": "Certified compost or anaerobic digestion",
    "E": "Packaging recycling",
}

CONDITIONS = ["fresh", "overripe", "bruised", "spoiled"]

# dated = carries an expiry date; feed_ok = suitable for feed if
# not expired; fixed = always this tier
CATALOG = {
    "bread": {"label": "Bread / bakery", "dated": True, "feed_ok": True},
    "biscuits": {"label": "Biscuits / snacks", "dated": True,
                 "feed_ok": True},
    "grains": {"label": "Grains / flour", "dated": True, "feed_ok": True},
    "dairy": {"label": "Milk / curd / dairy", "dated": True,
              "feed_ok": False},
    "ready_pack": {"label": "Ready-to-eat pack", "dated": True,
                   "feed_ok": False},
    "tomato": {"label": "Tomato", "dated": False, "feed_ok": True},
    "banana": {"label": "Banana", "dated": False, "feed_ok": True},
    "greens": {"label": "Leafy greens", "dated": False, "feed_ok": True},
    "kitchen_waste": {"label": "Mixed kitchen waste", "dated": False,
                      "feed_ok": False, "fixed": "D"},
    "packaging": {"label": "Empty packaging", "dated": False,
                  "feed_ok": False, "fixed": "E"},
}


def _out(tier, locked, reason, urgency, days_left):
    allowed = ["E"] if tier == "E" else [
        t for t in "ABCD" if t not in locked]
    return {
        "tier": tier,
        "tier_name": TIERS[tier],
        "route": TIER_ROUTES[tier],
        "allowed": allowed,
        "locked": list(locked),
        "reason": reason,
        "urgency": urgency,
        "days_left": days_left,
    }


def classify(item, condition="fresh", expiry=None, today=None,
             expired=False):
    """Return the tier and which routes are locked."""
    if item not in CATALOG:
        raise ValueError(f"Unknown item: {item}")
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    info = CATALOG[item]
    today = today or date.today()

    if info.get("fixed"):
        t = info["fixed"]
        why = "Fixed route for this item type."
        return _out(t, [], why, "low", None)

    days_left = (expiry - today).days if expiry else None
    is_expired = expired or (days_left is not None and days_left < 0)

    if is_expired:
        why = ("Expired: human-food, process and feed routes are "
               "locked. Certified compost or digestion only.")
        return _out("D", ["A", "B", "C"], why, "high", days_left)

    if condition == "spoiled":
        why = "Spoiled: only certified compost or digestion."
        return _out("D", ["A", "B", "C"], why, "high", days_left)

    if condition == "bruised":
        if info["feed_ok"]:
            why = "Not fit for people but safe: feed route."
            return _out("C", ["A"], why, "medium", days_left)
        why = "Damaged and not feed-suitable: certified compost."
        return _out("D", ["A", "B", "C"], why, "medium", days_left)

    if condition == "overripe":
        why = "Overripe but usable: processing units."
        return _out("B", ["A"], why, "high", days_left)

    urgency = "low"
    if days_left is not None:
        urgency = ("high" if days_left <= 2
                   else "medium" if days_left <= 7 else "low")
    why = "Within date and fit for use: rescue first."
    return _out("A", [], why, urgency, days_left)


def escalate(tier, locked):
    """Next allowed tier if a lot is unclaimed (A>B>C>D)."""
    order = "ABCD"
    if tier not in order:
        return tier
    for t in order[order.index(tier) + 1:]:
        if t not in locked:
            return t
    return "D"
