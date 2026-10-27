"""Rule engine: expiry date + condition + item decides the route.

FoodLoop is paid by businesses to dispose of waste, so it only takes
food that is already waste: expired, spoiled or damaged. Food that is
still in date and in good condition has value and is refused (there is
no rescue / resale route; the old tier A was retired).

Key rule: once food is expired (or spoiled) the process and feed
tiers are LOCKED. Expired food can only go to certified compost /
anaerobic digestion (Recover). Feed is only for non-expired damaged food.
Confirm the legal details with FSSAI before use.
"""
from datetime import date

# The keys below are stored in the database and in issued disposal
# records, so they never change. People see the letters in TIER_LETTER
# (A, B, C, D in order), which is what every screen and PDF shows.
TIER_LETTER = {"B": "A", "C": "B", "D": "C", "E": "D"}

TIERS = {
    "B": "Process",
    "C": "Feed",
    "D": "Recover",
    "E": "Packaging",
}

TIER_ROUTES = {
    "B": "Pulp, jam, pickle, dehydration units",
    "C": "Animal feed makers (non-expired surplus only)",
    "D": "Certified compost or anaerobic digestion",
    "E": "Packaging recycling",
}

CONDITIONS = ["fresh", "overripe", "bruised", "spoiled"]

# Items are food CATEGORIES, because the route depends on the kind of
# food, not the brand: dated = carries an expiry / use-by date;
# feed_ok = safe for animal feed if not expired; fixed = always this tier.
CATALOG = {
    "vegetables": {"label": "Vegetables", "dated": False, "feed_ok": True},
    "fruits": {"label": "Fruits", "dated": False, "feed_ok": True},
    "dairy": {"label": "Dairy", "dated": True, "feed_ok": False},
    "bakery": {"label": "Bakery and bread", "dated": True,
               "feed_ok": True},
    "grains": {"label": "Grains, flour and pulses", "dated": True,
               "feed_ok": True},
    "snacks": {"label": "Packaged snacks and biscuits", "dated": True,
               "feed_ok": True},
    "cooked": {"label": "Cooked and ready-to-eat food", "dated": True,
               "feed_ok": False},
    "kitchen_waste": {"label": "Mixed kitchen waste", "dated": False,
                      "feed_ok": False, "fixed": "D"},
    "packaging": {"label": "Empty packaging", "dated": False,
                  "feed_ok": False, "fixed": "E"},
}

# Old single-product keys already stored on lots map to their category.
LEGACY_ITEMS = {"tomato": "vegetables", "greens": "vegetables",
                "banana": "fruits", "bread": "bakery",
                "biscuits": "snacks", "ready_pack": "cooked"}


def resolve(item):
    return LEGACY_ITEMS.get(item, item)


def item_info(item):
    return CATALOG[resolve(item)]


def tier_letter(t):
    return TIER_LETTER.get(t, t)


def tier_name(t):
    """Display name; tolerates the retired tier A on old rows."""
    return TIERS.get(t) or ("Rescue (retired)" if t == "A" else t)


def _out(tier, locked, reason, urgency, days_left):
    allowed = ["E"] if tier == "E" else [
        t for t in "BCD" if t not in locked]
    return {
        "tier": tier,
        "tier_name": tier_name(tier),
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
    item = resolve(item)
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
        return _out("D", ["B", "C"], why, "high", days_left)

    if condition == "spoiled":
        why = "Spoiled: only certified compost or digestion."
        return _out("D", ["B", "C"], why, "high", days_left)

    if condition == "bruised":
        if info["feed_ok"]:
            why = "Not fit for people but safe: feed route."
            return _out("C", [], why, "medium", days_left)
        why = "Damaged and not feed-suitable: certified compost."
        return _out("D", ["B", "C"], why, "medium", days_left)

    if condition == "overripe":
        why = "Overripe but usable: processing units."
        return _out("B", [], why, "high", days_left)

    raise ValueError(
        "This food is still in date and in good condition, so it isn't "
        "waste. FoodLoop only collects expired, spoiled or damaged food.")


def escalate(tier, locked):
    """Next allowed tier if a lot is unclaimed (B>C>D)."""
    order = "BCD"
    if tier not in order:
        return tier
    for t in order[order.index(tier) + 1:]:
        if t not in locked:
            return t
    return "D"
