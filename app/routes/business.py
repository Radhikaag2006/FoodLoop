from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from .. import config as C
from .. import tracking as T
from ..billing import require_access
from ..clock import iso, local_day
from ..db import get_db
from ..deps import need
from ..matching import rank_facilities
from ..models import Facility, Lot, Org, Pickup, PickupLine
from ..security import clean, norm_phone
from ..tiers import CATALOG, classify, item_info, resolve, tier_name
from .shared import csv_response, facility_card, pickup_dict

router = APIRouter(prefix="/api/business")
biz = need("business")


class LotIn(BaseModel):
    item: str
    condition: str = "fresh"
    qty_kg: float
    expiry: Optional[date] = None


def _check(b):
    if b.item not in CATALOG:
        raise HTTPException(422, "Choose an item.")
    if not (0 < b.qty_kg <= 100000):
        raise HTTPException(422, "Enter a quantity in kg.")
    if CATALOG[b.item]["dated"] and not b.expiry:
        raise HTTPException(422, "Add the expiry date for this item.")
    try:
        return classify(b.item, b.condition, b.expiry)
    except ValueError as e:
        raise HTTPException(422, str(e))


def _best_match(db, org, tier, kg):
    """Only the single best plant, and never its price or fee."""
    ranked = rank_facilities(db, tier, org.lat, org.lng, kg, 1)
    return facility_card(db, ranked[0]["facility"],
                         ranked[0]["distance_km"]) if ranked else None


def _with_matches(db, org, info, kg):
    info["match"] = _best_match(db, org, info["tier"], kg)
    return info


def _own_view(d):
    """Drop the route: it lists other businesses' names and phones."""
    return {k: v for k, v in d.items() if k != "route"}


def _lot(lot, code=""):
    return {"track_code": code, "id": lot.id, "item": item_info(lot.item)["label"],
            "key": resolve(lot.item), "condition": lot.condition,
            "qty_kg": lot.qty_kg,
            "expiry": lot.expiry.isoformat() if lot.expiry else "",
            "tier": lot.tier, "tier_name": tier_name(lot.tier),
            "status": "planned" if lot.pickup_id else "waiting",
            "pickup_id": lot.pickup_id, "at": iso(lot.created_at)}


@router.post("/preview")
def preview(b: LotIn, db=Depends(get_db), u=Depends(biz)):
    return _with_matches(db, db.get(Org, u.org_id), _check(b), b.qty_kg)


@router.post("/lots")
def add_lot(b: LotIn, db=Depends(get_db), u=Depends(biz)):
    info = _check(b)
    require_access(db, u.org_id)       # free trial, plan or unpaid dues
    lot = Lot(org_id=u.org_id, item=b.item, condition=b.condition,
              qty_kg=b.qty_kg, expiry=b.expiry, tier=info["tier"])
    db.add(lot)
    db.flush()
    code = T.code_for(db, lot.id)
    db.commit()
    info = _with_matches(db, db.get(Org, u.org_id), info, b.qty_kg)
    info["lot"] = _lot(lot, code)
    return info


@router.get("/lots")
def lots(db=Depends(get_db), u=Depends(biz)):
    rows = db.scalars(select(Lot).where(Lot.org_id == u.org_id)
                      .order_by(Lot.id.desc()).limit(100)).all()
    codes = T.codes_for(db, rows)
    db.commit()                 # older lots get their ID the first time
    return [_lot(x, codes[x.id]) for x in rows]


def _pickup_for(db, p, org_id):
    """One pickup as seen by a single business: only its own stop and
    lots, never other businesses' names or contacts."""
    d = pickup_dict(db, p)
    fac = db.get(Facility, p.facility_id)
    lines = db.scalars(select(PickupLine).where(
        PickupLine.pickup_id == p.id, PickupLine.org_id == org_id)).all()
    mine = sum(x.kg for x in lines)
    items = []
    for ln in lines:
        lot = db.get(Lot, ln.ref_id) if ln.ref_type == "lot" else None
        items.append({"lot_id": lot.id if lot else None,
                      "item": item_info(lot.item)["label"] if lot else "",
                      "kg": round(ln.kg, 2), "tier": ln.tier,
                      "tier_name": tier_name(ln.tier)})
    stop = next((s for s in d["route"] if s["org_id"] == org_id), None)
    return {
        "id": p.id, "status": p.status, "record": d["record"],
        "facility": fac.name, "facility_kind": fac.kind,
        "facility_address": fac.address, "facility_phone": fac.phone,
        "certified": fac.certified, "cert_no": fac.cert_no,
        "facility_card": facility_card(db, fac),
        "schedule": d["schedule"],
        "created_at": d["created_at"], "closed_at": d["closed_at"],
        "your_kg": round(mine, 1), "expected_kg": p.expected_kg,
        "hub_kg": p.hub_kg, "facility_kg": p.facility_kg,
        "mismatch": p.mismatch, "stops": len(d["route"]),
        "route_km": p.route_km,
        "pickup_from": {"address": stop["address"],
                        "point": stop["point"]} if stop else None,
        "co2e_kg": round(mine * C.CO2E_KG_PER_KG_FOOD, 1)
        if p.status == "closed" else None,
        "lots": items,
    }


@router.get("/lots/{lid}")
def lot_detail(lid: int, request: Request, db=Depends(get_db),
               u=Depends(biz)):
    lot = db.get(Lot, lid)
    if not lot or lot.org_id != u.org_id:
        raise HTTPException(404, "Lot not found.")
    code = T.code_for(db, lot.id)
    db.commit()
    out = _lot(lot, code)
    out["track"] = T.qr_for(str(request.base_url), code)
    why = classify(lot.item, lot.condition, lot.expiry)
    out.update(route=why["route"], reason=why["reason"],
               locked=why["locked"], urgency=why["urgency"],
               days_left=why["days_left"])
    org = db.get(Org, u.org_id)
    out["verify_status"] = org.verify_status
    if lot.pickup_id:
        out["pickup"] = _pickup_for(db, db.get(Pickup, lot.pickup_id),
                                    u.org_id)
    else:
        out["match"] = _best_match(db, org, lot.tier, lot.qty_kg)
    return out


@router.get("/pickups/{pid}")
def pickup_detail(pid: int, db=Depends(get_db), u=Depends(biz)):
    p = db.get(Pickup, pid)
    has = p and db.scalar(select(PickupLine.id).where(
        PickupLine.pickup_id == pid, PickupLine.org_id == u.org_id))
    if not has:
        raise HTTPException(404, "Pickup not found.")
    return _pickup_for(db, p, u.org_id)


@router.delete("/lots/{lid}")
def del_lot(lid: int, db=Depends(get_db), u=Depends(biz)):
    lot = db.get(Lot, lid)
    if not lot or lot.org_id != u.org_id:
        raise HTTPException(404, "Lot not found.")
    if lot.pickup_id:
        raise HTTPException(409, "This lot is already in a pickup.")
    db.delete(lot)
    db.commit()
    return {"ok": True}


@router.get("/home")
def home(db=Depends(get_db), u=Depends(biz)):
    org = db.get(Org, u.org_id)
    ls = db.scalars(select(Lot).where(Lot.org_id == u.org_id)).all()
    waiting = [x for x in ls if not x.pickup_id]
    by_tier = {}
    for x in waiting:
        by_tier[x.tier] = by_tier.get(x.tier, 0) + x.qty_kg
    ids = set(db.scalars(select(PickupLine.pickup_id).where(
        PickupLine.org_id == u.org_id)))
    pk = [_own_view(pickup_dict(db, p)) for p in db.scalars(
        select(Pickup).order_by(Pickup.id.desc())) if p.id in ids]
    done = [p for p in pk if p["status"] == "closed"]
    lines = db.scalars(select(PickupLine).where(
        PickupLine.org_id == u.org_id,
        PickupLine.pickup_id.in_([p["id"] for p in done]))).all()
    kg_done = sum(x.kg for x in lines)
    return {
        "name": u.name, "org": org.name,
        "verify_status": org.verify_status, "fssai_no": org.fssai_no,
        "waiting_kg": round(sum(x.qty_kg for x in waiting), 1),
        "waiting_lots": len(waiting), "by_tier": by_tier,
        "planned": sum(1 for p in pk if p["status"] in
                       ("planned", "collected")),
        "disposed_kg": round(kg_done, 1),
        "records": len(done),
        "co2e_kg": round(kg_done * C.CO2E_KG_PER_KG_FOOD, 1),
        "recent": pk[:3]}


@router.get("/pickups")
def pickups(db=Depends(get_db), u=Depends(biz)):
    ids = set(db.scalars(select(PickupLine.pickup_id).where(
        PickupLine.org_id == u.org_id)))
    rows = db.scalars(select(Pickup).order_by(Pickup.id.desc())).all()
    return [_own_view(pickup_dict(db, p)) for p in rows if p.id in ids][:40]


class ProfileIn(BaseModel):
    name: str
    business_type: str = ""
    fssai_no: str = ""
    address: str
    contact_phone: str


@router.put("/profile")
def profile(b: ProfileIn, db=Depends(get_db), u=Depends(biz)):
    o = db.get(Org, u.org_id)
    o.name = clean(b.name, 120, "Business name")
    o.address = clean(b.address, 200, "Address")
    o.business_type = b.business_type[:30]
    o.contact_phone = norm_phone(b.contact_phone)
    f = b.fssai_no.strip()[:20]
    if f != o.fssai_no and o.verify_status == "verified":
        o.verify_status = "pending"          # re-check changed licence
    o.fssai_no = f
    db.commit()
    return {"ok": True}


@router.get("/report.csv")
def report(db=Depends(get_db), u=Depends(biz)):
    ids = set(db.scalars(select(PickupLine.pickup_id).where(
        PickupLine.org_id == u.org_id)))
    out = [["record", "pickup", "status", "closed", "facility", "tier",
            "kg_from_you", "weights_match"]]
    for p in db.scalars(select(Pickup).where(Pickup.id.in_(ids))
                        .order_by(Pickup.id)):
        d = pickup_dict(db, p)
        for ln in db.scalars(select(PickupLine).where(
                PickupLine.pickup_id == p.id,
                PickupLine.org_id == u.org_id)):
            out.append([d["record"], p.id, p.status,
                        local_day(p.closed_at) if p.closed_at else "",
                        d["facility"], ln.tier, round(ln.kg, 2),
                        ("no" if p.mismatch else "yes")
                        if p.status == "closed" else ""])
    return csv_response(out, "foodloop-disposal-report.csv")
