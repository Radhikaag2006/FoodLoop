"""Dispatch: who drives a run, and what the driver is paid.

A run goes to the collector who
  * is switched on and signed in as active,
  * has a vehicle big enough for the whole run (capacity_kg), and
  * is closest to the first stop, counting each run they already hold as
    DISPATCH_LOAD_KM extra so work spreads out.
If nobody fits, the run stays unassigned and any collector may claim it.

Driver fare = base + per road km + per extra stop + per kg. Distances
are straight lines scaled by ROAD_FACTOR; all rates are placeholders in
config.py."""
import json

from sqlalchemy import func, select

from . import config as C
from .clock import utcnow
from .deps import notify, notify_role
from .matching import haversine
from .models import (CollectorProfile, Facility, Pickup, PickupLine,
                     PickupSchedule, RunAssignment, User)


# ---------- the driver's fare ----------
def trip_km(base, stops, fac):
    """Road km: base -> every stop -> plant -> back to base."""
    pts = [(s["lat"], s["lng"]) for s in stops] + [(fac.lat, fac.lng)]
    if base:
        pts = [base] + pts + [base]
    return sum(haversine(a[0], a[1], b[0], b[1])
               for a, b in zip(pts, pts[1:])) * C.ROAD_FACTOR


def driver_fare(km, kg, n_stops):
    """Returns (total paise, breakdown paise)."""
    parts = {"base": C.DRIVER_BASE_PAISE,
             "distance": round(km * C.DRIVER_PER_KM_PAISE),
             "stops": max(0, n_stops - 1) * C.DRIVER_PER_STOP_PAISE,
             "weight": round(kg * C.DRIVER_PER_KG_PAISE)}
    return sum(parts.values()), parts


def _base_of(db, user_id):
    prof = user_id and db.scalar(select(CollectorProfile).where(
        CollectorProfile.user_id == user_id))
    return (prof.base_lat, prof.base_lng) if prof and (
        prof.base_lat or prof.base_lng) else None


def fare_for(db, p, user_id=None):
    """What `user_id` would be paid for run `p` (their own base is used)."""
    fac = db.get(Facility, p.facility_id)
    stops = json.loads(p.route)
    kg = p.hub_kg or p.expected_kg
    km = trip_km(_base_of(db, user_id), stops, fac)
    total, parts = driver_fare(km, kg, len(stops))
    return {"total_paise": total, "total": round(total / 100, 2),
            "km": round(km, 1), "stops": len(stops), "kg": round(kg, 1),
            "parts": {k: round(v / 100, 2) for k, v in parts.items()}}


# ---------- collectors ----------
def _live_profiles(db):
    """(profile, user) of collectors who can take work right now."""
    return db.execute(
        select(CollectorProfile, User)
        .join(User, User.id == CollectorProfile.user_id)
        .where(CollectorProfile.available, CollectorProfile.capacity_kg > 0,
               User.status == "active", User.role == "hub")).all()


def max_capacity(db):
    """Biggest vehicle on the road, or None if no one has set one up."""
    caps = [pr.capacity_kg for pr, _ in _live_profiles(db)]
    return max(caps) if caps else None


def _open_counts(db):
    rows = db.execute(
        select(RunAssignment.collector_id, func.count(RunAssignment.id))
        .join(Pickup, Pickup.id == RunAssignment.pickup_id)
        .where(Pickup.status.in_(("planned", "collected")),
               RunAssignment.collector_id.is_not(None))
        .group_by(RunAssignment.collector_id)).all()
    return {cid: n for cid, n in rows}


def rank_collectors(db, p, exclude=()):
    stops = json.loads(p.route)
    fac = db.get(Facility, p.facility_id)
    first = (stops[0]["lat"], stops[0]["lng"]) if stops else (fac.lat, fac.lng)
    busy = _open_counts(db)
    out = []
    for pr, u in _live_profiles(db):
        if u.id in exclude or pr.capacity_kg < p.expected_kg:
            continue
        d = haversine(pr.base_lat, pr.base_lng, first[0], first[1])
        out.append((d + C.DISPATCH_LOAD_KM * busy.get(u.id, 0), d, u))
    out.sort(key=lambda r: (r[0], r[2].id))
    return out


def assignment_of(db, pid):
    return db.scalar(select(RunAssignment).where(
        RunAssignment.pickup_id == pid))


def owner_of(db, pid):
    """The collector responsible for a run, or None."""
    a = assignment_of(db, pid)
    if a and a.collector_id:
        return a.collector_id
    s = db.scalar(select(PickupSchedule).where(
        PickupSchedule.pickup_id == pid))
    return s.collector_id if s else None


def assign_run(db, p, exclude=()):
    """Give run `p` to the best collector (or leave it open)."""
    a = assignment_of(db, p.id)
    if not a:
        a = RunAssignment(pickup_id=p.id)
        db.add(a)
    ranked = rank_collectors(db, p, exclude)
    a.collector_id = ranked[0][2].id if ranked else None
    a.accepted_at = None               # a new offer needs a new yes
    if ranked:
        f = fare_for(db, p, a.collector_id)
        notify(db, a.collector_id, "New run assigned",
               f"Run #{p.id}: {p.expected_kg:g} kg, {f['stops']} stop"
               f"{'s' if f['stops'] != 1 else ''}, about "
               f"Rs {f['total']:.0f} for the trip.", kind="info")
    db.flush()
    return a


def claim(db, p, user):
    """An open run is taken by the collector who acts on it first.
    Acting on a run (booking a time, collecting it) means accepting it."""
    a = assignment_of(db, p.id)
    if not a:
        a = RunAssignment(pickup_id=p.id)
        db.add(a)
    a.collector_id = user.id
    a.accepted_at = a.accepted_at or utcnow()
    db.flush()
    return a


def accept(db, p, user):
    """The collector says yes to an offered (or open) run."""
    a = claim(db, p, user)
    if not a.accepted_at:
        a.accepted_at = utcnow()
    return a


def is_accepted(db, p):
    """Offered runs wait for a yes; booked or started runs already have one."""
    a = assignment_of(db, p.id)
    if a and a.accepted_at:
        return True
    if p.status != "planned":
        return True
    return bool(db.scalar(select(PickupSchedule.id).where(
        PickupSchedule.pickup_id == p.id)))


def decline(db, p, user):
    """Hand a run back; it goes to the next best collector."""
    a = assignment_of(db, p.id)
    gone = set(json.loads(a.declined)) | {user.id}
    a.declined = json.dumps(sorted(gone))
    s = db.scalar(select(PickupSchedule).where(
        PickupSchedule.pickup_id == p.id))
    if s:                              # the booked time was theirs
        db.delete(s)
        for oid in {ln.org_id for ln in db.scalars(select(PickupLine).where(
                PickupLine.pickup_id == p.id))}:
            notify_role(db, "business", "Collector changed",
                        f"Pickup #{p.id} has a new collector. "
                        "A new time will be confirmed.", org_id=oid)
    return assign_run(db, p, exclude=gone)


def settle(db, p):
    """Freeze the driver's fare when a run is closed."""
    a = assignment_of(db, p.id)
    if a and a.collector_id:
        a.fare_paise = fare_for(db, p, a.collector_id)["total_paise"]
