"""Order tracking: every lot gets a unique tracking ID (and QR).

Anyone holding the ID can see where the waste is and what finally
happened to it. The public view deliberately leaves out who the
business is and who the collector is: it shows the waste's journey, the
plant it reached and how it was used, never people's names or numbers."""
import re

import segno
from sqlalchemy import select

from . import config as C
from .clock import IST, iso
from .models import (Facility, Lot, PickupSchedule, Pickup, Record,
                     RunEvent, Tracking)
from .routes.shared import WINDOW, facility_card
from .security import _ALPHA, make_code
from .tiers import item_info, tier_name

PREFIX = "FL-"
CODE_LEN = 8

# What happens to waste at each kind of plant (as listed by the admin).
USED_FOR = {
    "compost": "Turned into compost that enriches soil.",
    "biogas": "Digested to make biogas and bio-fertiliser.",
    "processor": "Processed into products such as pulp, pickle or "
                 "dehydrated food.",
    "feed": "Used as animal feed.",
    "recycler": "Sent for recycling.",
}

STATE = {
    "placed": "Order placed",
    "planned": "Pickup planned",
    "scheduled": "Pickup scheduled",
    "in_transit": "On the way to the plant",
    "delivered": "Delivered and processed",
}


# ---------- codes ----------
def norm(raw: str) -> str:
    """'fl 7k2p-9qxm', 'FL-7K2P9QXM' and '7k2p9qxm' are the same ID."""
    s = re.sub(r"[^A-Za-z0-9]", "", raw or "").upper()
    if len(s) == CODE_LEN + 2 and s.startswith("FL"):
        s = s[2:]
    return PREFIX + s if len(s) == CODE_LEN else ""


def code_for(db, lot_id: int) -> str:
    row = db.scalar(select(Tracking).where(Tracking.lot_id == lot_id))
    if row:
        return row.code
    while True:
        code = PREFIX + make_code(CODE_LEN)
        if not db.scalar(select(Tracking.id).where(Tracking.code == code)):
            break
    db.add(Tracking(lot_id=lot_id, code=code))
    db.flush()
    return code


def codes_for(db, lots) -> dict:
    """Codes for many lots at once (older lots get theirs on first look)."""
    ids = [x.id for x in lots]
    have = {t.lot_id: t.code for t in db.scalars(
        select(Tracking).where(Tracking.lot_id.in_(ids)))} if ids else {}
    for lot in lots:
        if lot.id not in have:
            have[lot.id] = code_for(db, lot.id)
    return have


def lot_by_code(db, raw: str):
    code = norm(raw)
    t = code and db.scalar(select(Tracking).where(Tracking.code == code))
    return db.get(Lot, t.lot_id) if t else None


def qr_for(base_url: str, code: str) -> dict:
    url = f"{base_url.rstrip('/')}/track/{code}"
    return {"code": code, "url": url,
            "qr": segno.make(url, error="m").svg_data_uri(scale=6, border=2)}


# ---------- the journey of a run ----------
def event(db, pickup_id: int, kind: str, user_id=None):
    """Remember when a run reached a stage (a new time replaces the old
    one for 'scheduled'; the other stages are recorded once)."""
    old = db.scalar(select(RunEvent).where(
        RunEvent.pickup_id == pickup_id, RunEvent.kind == kind))
    if old and kind != "scheduled":
        return
    if old:
        db.delete(old)
        db.flush()
    db.add(RunEvent(pickup_id=pickup_id, kind=kind, by_user=user_id))


def _at(db, pid, kind):
    e = db.scalar(select(RunEvent).where(
        RunEvent.pickup_id == pid, RunEvent.kind == kind))
    return e.at if e else None


def _when(dt):
    return (dt + IST).strftime("%a %d %b, %I:%M %p").replace(" 0", " ")


def _hm(dt):
    return (dt + IST).strftime("%I:%M %p").lstrip("0")


def view(db, lot) -> dict:
    """The public tracking page for one lot."""
    info = item_info(lot.item)
    p = db.get(Pickup, lot.pickup_id) if lot.pickup_id else None
    fac = db.get(Facility, p.facility_id) if p else None
    sched = p and db.scalar(select(PickupSchedule).where(
        PickupSchedule.pickup_id == p.id))
    rec = p and db.scalar(select(Record).where(Record.pickup_id == p.id))
    closed = bool(p and p.status == "closed")
    collected = bool(p and p.status in ("collected", "closed"))
    confirmed = (round(lot.qty_kg * p.hub_kg / p.expected_kg, 1)
                 if closed and p.expected_kg and p.hub_kg else None)

    if closed:
        state = "delivered"
    elif collected:
        state = "in_transit"
    elif sched:
        state = "scheduled"
    elif p:
        state = "planned"
    else:
        state = "placed"

    plan_detail = ""
    if p:
        plan_detail = f"Matched to {fac.name}."
        if sched:
            plan_detail += (f" Collector arriving {_when(sched.starts_at)} "
                            f"to {_hm(sched.starts_at + WINDOW)}.")
    steps = [
        {"key": "placed", "title": "Order placed", "done": True,
         "at": iso(lot.created_at),
         "detail": f"{info['label']}, {lot.qty_kg:g} kg"},
        {"key": "planned", "title": "Pickup planned", "done": bool(p),
         "at": iso(_at(db, p.id, "planned") or p.created_at) if p else None,
         "detail": plan_detail or "Waiting for enough waste to plan a run."},
        {"key": "collected", "title": "Collected from you",
         "done": collected,
         "at": iso(_at(db, p.id, "collected")) if collected else None,
         "detail": "Picked up by a FoodLoop collector." if collected
         else "A collector will pick it up."},
        {"key": "transit", "title": "On the way to the plant",
         "done": closed,
         "detail": (f"Taken to {fac.name}." if collected and fac
                    else "Starts once it is collected.")},
        {"key": "arrived", "title": "Reached the plant", "done": closed,
         "at": iso(p.closed_at) if closed else None,
         "detail": (f"Weighed at {fac.name}"
                    + (f": {confirmed:g} kg confirmed." if confirmed else ".")
                    + (" Weights differ by more than 5%, flagged on the "
                       "record." if p.mismatch else "")) if closed
         else "Not there yet."},
        {"key": "used", "title": "How it was used", "done": closed,
         "detail": (USED_FOR.get(fac.kind, "Disposed of safely.")
                    + (" Certified facility." if fac.certified else ""))
         if closed else "Shown once it has been processed."},
    ]
    now = next((i for i, s in enumerate(steps) if not s["done"]), None)
    if now is not None:
        steps[now]["current"] = True
    return {
        "code": (db.scalar(select(Tracking.code).where(
            Tracking.lot_id == lot.id)) or ""),
        "state": state, "state_label": STATE[state], "steps": steps,
        "item": {"label": info["label"], "kg": lot.qty_kg,
                 "condition": lot.condition, "tier_name": tier_name(lot.tier)},
        "plant": facility_card(db, fac) if fac else None,
        "how_used": USED_FOR.get(fac.kind, "Disposed of safely.")
        if closed else None,
        "record": rec.code if rec else "",
        "confirmed_kg": confirmed,
        "weights_match": (not p.mismatch) if closed else None,
        "co2e_kg": round(confirmed * C.CO2E_KG_PER_KG_FOOD, 1)
        if confirmed else None,
        "placed_at": iso(lot.created_at),
    }
