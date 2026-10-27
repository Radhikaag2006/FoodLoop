from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from .. import config as C
from .. import billing as B
from .. import dispatch as D
from .. import payments as P
from .. import tracking as T
from ..clock import IST, utcnow
from ..db import get_db
from ..deps import need, notify_role
from ..matching import plan_pickups
from ..models import (CollectorProfile, Facility, Invoice, Lot, Org, Pickup,
                      PickupLine, PickupSchedule, RunAssignment, User)
from ..billing import charge_pickup
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
    # big groups are cut to the biggest vehicle, then each run is offered
    # to the nearest collector whose vehicle can carry it
    created, waiting = plan_pickups(db, b.min_kg, D.max_capacity(db))
    D.dispatch_new(db, created)          # rules, solver batch or shadow
    for p in created:
        T.event(db, p.id, "planned", u.id)
    for p in created:
        for oid in {ln.org_id for ln in db.scalars(select(PickupLine)
                    .where(PickupLine.pickup_id == p.id))}:
            notify_role(db, "business", "Pickup planned",
                        f"A pickup of your lots is planned (#{p.id}).",
                        org_id=oid)
    db.commit()
    return {"created": [_run_view(db, p, u) for p in created],
            "waiting": waiting}


def _run_view(db, p, viewer):
    """A run as a collector sees it: who has it, and the driver fare."""
    owner = D.owner_of(db, p.id)
    a = D.assignment_of(db, p.id)
    fare = D.fare_for(db, p, owner or viewer.id)
    if a and a.fare_paise is not None:              # frozen at close
        fare["total_paise"], fare["total"] = a.fare_paise, round(
            a.fare_paise / 100, 2)
    d = pickup_dict(db, p)
    pending = bool(a and a.pending)
    d.update(assigned_to=db.get(User, owner).name if owner else None,
             mine=owner == viewer.id, open=owner is None and not pending,
             pending=pending, fare=fare, accepted=D.is_accepted(db, p))
    if viewer.role == "admin" and a:           # admin only: why this driver
        d["why"] = a.reason
    return d


@router.get("/week")
def week(db=Depends(get_db), u=Depends(hub)):
    """The collector's dashboard: runs on offer (with pay and distance) and
    the next seven days of accepted runs, with what each day pays."""
    today = (utcnow() + IST).date()
    days = {today + timedelta(days=i): [] for i in range(7)}
    offers, later, unscheduled = [], [], []
    for p in db.scalars(select(Pickup).where(
            Pickup.status.in_(("planned", "collected")))
            .order_by(Pickup.id)):
        owner = D.owner_of(db, p.id)
        if owner not in (None, u.id):
            continue
        v = _run_view(db, p, u)
        if v["pending"]:                       # not given out yet
            continue
        if not v["accepted"]:
            offers.append(v)
            continue
        if owner != u.id:
            continue
        st = v["schedule"] and v["schedule"]["starts"]
        if not st:
            unscheduled.append(v)
            continue
        day = (datetime.fromisoformat(st.rstrip("Z")) + IST).date()
        if day >= today + timedelta(days=7):
            later.append(v)
        else:
            days[max(day, today)].append(v)    # overdue runs show today
    for r in days.values():
        r.sort(key=lambda x: x["schedule"]["starts"])
    cents = lambda rs: round(sum(r["fare"]["total_paise"] for r in rs) / 100, 2)
    since = utcnow() - timedelta(days=7)
    earned = db.scalar(
        select(func.coalesce(func.sum(RunAssignment.fare_paise), 0))
        .join(Pickup, Pickup.id == RunAssignment.pickup_id)
        .where(RunAssignment.collector_id == u.id,
               Pickup.status == "closed", Pickup.closed_at >= since)) or 0
    booked = [r for rs in days.values() for r in rs] + later + unscheduled
    return {
        "days": [{"date": d.isoformat(), "runs": rs, "total": cents(rs)}
                 for d, rs in days.items()],
        "later": later, "unscheduled": unscheduled, "offers": offers,
        "week_total": cents(booked), "week_runs": len(booked),
        "week_km": round(sum(r["fare"]["km"] for r in booked), 1),
        "earned_7d": round(earned / 100, 2),
    }


@router.post("/runs/{pid}/accept")
def accept(pid: int, db=Depends(get_db), u=Depends(hub)):
    """Say yes to an offered run, judged on its pay and distance."""
    p = db.get(Pickup, pid)
    if not p or p.status != "planned":
        raise HTTPException(409, "This run can't be accepted any more.")
    owner = D.owner_of(db, pid)
    if owner and owner != u.id:
        raise HTTPException(403, "This run is assigned to another collector.")
    D.accept(db, p, u)
    db.commit()
    return _run_view(db, p, u)


@router.get("/runs")
def runs(status: str = "open", db=Depends(get_db), u=Depends(hub)):
    st = select(Pickup).order_by(Pickup.id.desc())
    if status == "open":
        st = st.where(Pickup.status.in_(("planned", "collected")))
    elif status == "closed":
        st = st.where(Pickup.status == "closed")
    rows = [_run_view(db, p, u) for p in db.scalars(st.limit(60))]
    has_vehicle = db.scalar(select(CollectorProfile.id).where(
        CollectorProfile.user_id == u.id))
    if u.role == "hub":
        rows = [r for r in rows if not r["pending"]]
    if u.role == "hub" and has_vehicle:      # only mine, plus open ones
        rows = [r for r in rows if r["mine"] or r["open"]]
    return rows


def _owner_org_ids(db, pid):
    return {ln.org_id for ln in db.scalars(select(PickupLine).where(
        PickupLine.pickup_id == pid))}


def _when(dt):
    return (dt + IST).strftime("%a %d %b, %I:%M %p").replace(" 0", " ")


class ScheduleIn(BaseModel):
    at: str      # ISO time with offset, e.g. 2026-10-28T10:00+05:30


@router.post("/runs/{pid}/schedule")
def schedule(pid: int, b: ScheduleIn, db=Depends(get_db), u=Depends(hub)):
    """The collector takes the run and tells businesses when they come."""
    p = db.get(Pickup, pid)
    if not p or p.status != "planned":
        raise HTTPException(409, "This run can't be scheduled any more.")
    try:
        at = datetime.fromisoformat(b.at)
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone(IST))
        at = at.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(422, "Enter a valid date and time.")
    now = utcnow()
    if at < now - timedelta(minutes=10) or at > now + timedelta(days=14):
        raise HTTPException(
            422, "Pick a time from now up to 14 days ahead.")
    owner = D.owner_of(db, pid)
    if owner and owner != u.id and u.role != "admin":
        raise HTTPException(
            403, "This run is already taken by another collector.")
    if owner in (None, u.id):          # acting on a run is accepting it
        D.accept(db, p, u)
    s = db.scalar(select(PickupSchedule).where(
        PickupSchedule.pickup_id == pid))
    if s:
        s.starts_at = at
    else:
        db.add(PickupSchedule(pickup_id=pid, collector_id=owner or u.id,
                              starts_at=at))
    who = db.get(User, owner or u.id)
    T.event(db, pid, "scheduled", u.id)
    for oid in _owner_org_ids(db, pid):
        notify_role(
            db, "business", "Pickup time set",
            f"Pickup #{pid}: {_when(at)}. Collector {who.name}"
            f"{', ' + who.phone if who.phone else ''}.", org_id=oid)
    db.commit()
    return _run_view(db, p, u)


@router.post("/runs/{pid}/collect")
def collect(pid: int, db=Depends(get_db), u=Depends(hub)):
    p = db.get(Pickup, pid)
    if not p or p.status != "planned":
        raise HTTPException(409, "This run can't be marked collected.")
    owner = D.owner_of(db, pid)
    if owner and owner != u.id and u.role != "admin":
        raise HTTPException(
            403, "This run is assigned to another collector.")
    if owner in (None, u.id):          # acting on a run is accepting it
        D.accept(db, p, u)
    if not db.scalar(select(PickupSchedule).where(
            PickupSchedule.pickup_id == pid)):   # no booked time
        db.add(PickupSchedule(pickup_id=pid, collector_id=owner or u.id,
                              starts_at=utcnow()))
    p.status = "collected"
    D.log_mark(db, pid, owner or u.id, "started_at")
    T.event(db, pid, "collected", u.id)
    for oid in {ln.org_id for ln in db.scalars(select(PickupLine).where(
            PickupLine.pickup_id == p.id))}:
        notify_role(db, "business", "Waste collected",
                    f"Pickup #{p.id} was collected.", org_id=oid)
    db.commit()
    return _run_view(db, p, u)


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
    T.event(db, pid, "closed", u.id)
    charge_pickup(db, p)
    D.settle(db, p)
    for oid in {ln.org_id for ln in db.scalars(select(PickupLine).where(
            PickupLine.pickup_id == p.id))}:
        notify_role(db, "business", "Disposal record ready",
                    f"Record {rec.code} is available.", org_id=oid,
                    kind="record")
    db.commit()
    return _run_view(db, p, u)


@router.get("/runs/{pid}/bills")
def bills(pid: int, db=Depends(get_db), u=Depends(hub)):
    """What each business on a finished run owes, with its UPI QR, so the
    collector can see the amount and chase or show it."""
    p = db.get(Pickup, pid)
    if not p:
        raise HTTPException(404, "Run not found.")
    if u.role != "admin" and D.owner_of(db, pid) != u.id:
        raise HTTPException(403, "This run isn't yours.")
    out = []
    for i in db.scalars(select(Invoice).where(
            Invoice.pickup_id == pid).order_by(Invoice.id)):
        org = db.get(Org, i.org_id)
        d = B.invoice_dict(db, i)
        d.update(org=org.name, phone=org.contact_phone, upi=None)
        if i.status == "due" and i.amount_paise > 0:
            d["upi"] = P.upi_payload(i.amount_paise, f"FL{i.id}",
                                     f"FoodLoop pickup {pid}")
        out.append(d)
    return out


@router.post("/runs/{pid}/decline")
def decline(pid: int, db=Depends(get_db), u=Depends(hub)):
    """Give a run back so it can go to the next collector."""
    p = db.get(Pickup, pid)
    if not p or p.status != "planned":
        raise HTTPException(409, "This run can't be handed back any more.")
    if D.owner_of(db, pid) != u.id:
        raise HTTPException(403, "This run isn't yours.")
    D.decline(db, p, u)
    db.commit()
    return {"ok": True}


class ProfileIn(BaseModel):
    vehicle: str = ""
    capacity_kg: float
    base_lat: float
    base_lng: float
    base_label: str = ""
    available: bool = True


def _profile(db, uid):
    pr = db.scalar(select(CollectorProfile).where(
        CollectorProfile.user_id == uid))
    return pr and {"vehicle": pr.vehicle, "capacity_kg": pr.capacity_kg,
                   "base_lat": pr.base_lat, "base_lng": pr.base_lng,
                   "base_label": pr.base_label, "available": pr.available}


@router.get("/profile")
def get_profile(db=Depends(get_db), u=Depends(hub)):
    return {"profile": _profile(db, u.id)}


@router.put("/profile")
def put_profile(b: ProfileIn, db=Depends(get_db), u=Depends(hub)):
    if not (0 < b.capacity_kg <= 50000):
        raise HTTPException(422, "Enter what your vehicle can carry, in kg.")
    if not (-90 <= b.base_lat <= 90 and -180 <= b.base_lng <= 180)             or not (b.base_lat or b.base_lng):
        raise HTTPException(422, "Choose where your vehicle starts from.")
    pr = db.scalar(select(CollectorProfile).where(
        CollectorProfile.user_id == u.id))
    if not pr:
        pr = CollectorProfile(user_id=u.id)
        db.add(pr)
    pr.vehicle = b.vehicle.strip()[:40]
    pr.capacity_kg, pr.available = b.capacity_kg, b.available
    pr.base_lat, pr.base_lng = b.base_lat, b.base_lng
    pr.base_label = b.base_label.strip()[:60]
    db.commit()
    return {"profile": _profile(db, u.id)}


@router.get("/facilities")
def facilities(db=Depends(get_db), u=Depends(hub)):
    rows = db.scalars(select(Facility).where(Facility.active)).all()
    return [{"id": f.id, "name": f.name, "kind": f.kind,
             "tiers": f.tiers, "lat": f.lat, "lng": f.lng,
             "certified": f.certified, "address": f.address,
             "phone": f.phone, "capacity_kg": f.capacity_kg}
            for f in rows]
