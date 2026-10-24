from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from .. import config as C
from ..clock import utcnow
from ..db import get_db
from ..deps import need, notify_role
from ..matching import plan_pickups
from ..models import Facility, Lot, Org, Pickup, PickupLine
from ..records import create_record
from .shared import pickup_dict

router = APIRouter(prefix="/api/hub")
hub = need("hub", "admin")


@router.get("/pool")
def pool(db=Depends(get_db), u=Depends(hub)):
    by_tier, by_org = {}, {}
    ls = db.scalars(select(Lot).where(Lot.pickup_id.is_(None)))
    for tier, org_id, kg in [(x.tier, x.org_id, x.qty_kg) for x in ls]:
        by_tier[tier] = by_tier.get(tier, 0) + kg
        by_org[org_id] = by_org.get(org_id, 0) + kg
    orgs = {o.id: o for o in db.scalars(select(Org))}
    rows = [{"org_id": i, "name": orgs[i].name, "kind": orgs[i].kind,
             "kg": round(kg, 1),
             "verified": orgs[i].verify_status == "verified"}
            for i, kg in by_org.items()]
    rows.sort(key=lambda r: -r["kg"])
    return {"by_tier": {k: round(v, 1) for k, v in by_tier.items()},
            "total": round(sum(by_tier.values()), 1),
            "orgs": rows, "min_kg": C.MIN_PICKUP_KG,
            "blocked_kg": round(sum(r["kg"] for r in rows
                                    if not r["verified"]), 1)}


class PlanIn(BaseModel):
    min_kg: Optional[float] = None


@router.post("/plan")
def plan(b: PlanIn, db=Depends(get_db), u=Depends(hub)):
    if b.min_kg is not None and b.min_kg < 0:
        raise HTTPException(422, "Minimum can't be negative.")
    created, waiting = plan_pickups(db, b.min_kg)
    for p in created:
        for oid in {ln.org_id for ln in db.scalars(select(PickupLine)
                    .where(PickupLine.pickup_id == p.id))}:
            notify_role(db, "business", "Pickup planned",
                        f"A pickup of your lots is planned (#{p.id}).",
                        org_id=oid)
    db.commit()
    return {"created": [pickup_dict(db, p) for p in created],
            "waiting": waiting}


@router.get("/runs")
def runs(status: str = "open", db=Depends(get_db), u=Depends(hub)):
    st = select(Pickup).order_by(Pickup.id.desc())
    if status == "open":
        st = st.where(Pickup.status.in_(("planned", "collected")))
    elif status == "closed":
        st = st.where(Pickup.status == "closed")
    return [pickup_dict(db, p) for p in db.scalars(st.limit(60))]


@router.post("/runs/{pid}/collect")
def collect(pid: int, db=Depends(get_db), u=Depends(hub)):
    p = db.get(Pickup, pid)
    if not p or p.status != "planned":
        raise HTTPException(409, "This run can't be marked collected.")
    p.status = "collected"
    for oid in {ln.org_id for ln in db.scalars(select(PickupLine).where(
            PickupLine.pickup_id == p.id))}:
        notify_role(db, "business", "Waste collected",
                    f"Pickup #{p.id} was collected.", org_id=oid)
    db.commit()
    return pickup_dict(db, p)


class CloseIn(BaseModel):
    hub_kg: float
    facility_kg: float


@router.post("/runs/{pid}/close")
def close(pid: int, b: CloseIn, db=Depends(get_db), u=Depends(hub)):
    p = db.get(Pickup, pid)
    if not p or p.status != "collected":
        raise HTTPException(409, "Mark the run collected first.")
    if b.hub_kg <= 0 or b.facility_kg <= 0:
        raise HTTPException(422, "Enter both weights in kg.")
    tol = C.HUB_TOLERANCE
    off1 = abs(b.hub_kg - p.expected_kg) / p.expected_kg
    off2 = abs(b.facility_kg - b.hub_kg) / b.hub_kg
    p.hub_kg, p.facility_kg = b.hub_kg, b.facility_kg
    p.mismatch = off1 > tol or off2 > tol
    p.status, p.closed_at = "closed", utcnow()
    db.flush()
    rec = create_record(db, p)
    for oid in {ln.org_id for ln in db.scalars(select(PickupLine).where(
            PickupLine.pickup_id == p.id))}:
        notify_role(db, "business", "Disposal record ready",
                    f"Record {rec.code} is available.", org_id=oid,
                    kind="record")
    db.commit()
    return pickup_dict(db, p)


@router.get("/facilities")
def facilities(db=Depends(get_db), u=Depends(hub)):
    rows = db.scalars(select(Facility).where(Facility.active)).all()
    return [{"id": f.id, "name": f.name, "kind": f.kind,
             "tiers": f.tiers, "lat": f.lat, "lng": f.lng,
             "certified": f.certified, "address": f.address,
             "phone": f.phone, "capacity_kg": f.capacity_kg}
            for f in rows]
