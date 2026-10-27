"""Dispatch: who drives a run, and what the driver is paid.

A run goes to the collector who
  * is switched on and signed in as active,
  * has a vehicle big enough for the whole run (capacity_kg), and
  * is closest to the first stop, counting each run they already hold as
    DISPATCH_LOAD_KM extra so work spreads out.
If nobody fits, the run stays unassigned and any collector may claim it.

With DISPATCH_MODE=solver all waiting runs are given out together by
optimizer.py (one batch per DISPATCH_BATCH_SECONDS); "shadow" keeps the
rules above and only records what the solver would have done.

Driver fare = base + per road km + per extra stop + per kg. Distances
are straight lines scaled by ROAD_FACTOR; all rates are placeholders in
config.py."""
import json
import logging
from datetime import timedelta

from sqlalchemy import func, select

from . import config as C
from . import optimizer as O
from .clock import IST, utcnow
from .deps import notify, notify_role
from .matching import haversine
from .models import (CollectorProfile, Facility, Pickup, PickupLine,
                     PickupSchedule, RunAssignment, TripLog, User)
from .travel import Travel

log = logging.getLogger("foodloop.dispatch")


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


def _open_counts(db, exclude=()):
    q = (select(RunAssignment.collector_id, func.count(RunAssignment.id))
         .join(Pickup, Pickup.id == RunAssignment.pickup_id)
         .where(Pickup.status.in_(("planned", "collected")),
                RunAssignment.collector_id.is_not(None)))
    if exclude:
        q = q.where(RunAssignment.pickup_id.not_in(list(exclude)))
    return {cid: n for cid, n in db.execute(q.group_by(
        RunAssignment.collector_id)).all()}


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


def assign_run(db, p, exclude=(), note=""):
    """Give run `p` to the best collector (or leave it open): the rules."""
    a = assignment_of(db, p.id)
    if not a:
        a = RunAssignment(pickup_id=p.id)
        db.add(a)
    ranked = rank_collectors(db, p, exclude)
    a.collector_id = ranked[0][2].id if ranked else None
    a.accepted_at = None               # a new offer needs a new yes
    a.pending = False
    a.reason = note + _rules_reason(db, p, ranked)
    a.planned_km = None
    if ranked:
        f = fare_for(db, p, a.collector_id)
        a.planned_km = f["km"]
        log_offer(db, p, a.collector_id, f["km"])
        notify(db, a.collector_id, "New run assigned",
               f"Run #{p.id}: {p.expected_kg:g} kg, {f['stops']} stop"
               f"{'s' if f['stops'] != 1 else ''}, about "
               f"Rs {f['total']:.0f} for the trip.", kind="info")
    db.flush()
    return a


def _rules_reason(db, p, ranked):
    if not ranked:
        return "no eligible driver: left open for any collector to claim"
    score, d, u = ranked[0]
    held = _open_counts(db, (p.id,)).get(u.id, 0)
    return (f"nearest eligible driver (rules), {d:.1f} km from the first "
            f"stop, capacity ok, holds {held} other run"
            f"{'' if held == 1 else 's'}")


def claim(db, p, user):
    """An open run is taken by the collector who acts on it first.
    Acting on a run (booking a time, collecting it) means accepting it."""
    a = assignment_of(db, p.id)
    if not a:
        a = RunAssignment(pickup_id=p.id)
        db.add(a)
    new_owner = a.collector_id != user.id
    a.collector_id = user.id
    a.pending = False
    a.accepted_at = a.accepted_at or utcnow()
    if new_owner or not _open_log(db, p.id, user.id):
        log_offer(db, p, user.id, fare_for(db, p, user.id)["km"])
    log_mark(db, p.id, user.id, "accepted_at")
    db.flush()
    return a


def accept(db, p, user):
    """The collector says yes to an offered (or open) run."""
    return claim(db, p, user)


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
    """Hand a run back; it goes to the next best collector. In solver mode
    this run and every other run still waiting for a yes are re-planned
    together, never giving a run back to someone who declined it."""
    a = assignment_of(db, p.id)
    gone = set(json.loads(a.declined)) | {user.id}
    a.declined = json.dumps(sorted(gone))
    log_mark(db, p.id, user.id, "declined_at")
    s = db.scalar(select(PickupSchedule).where(
        PickupSchedule.pickup_id == p.id))
    if s:                              # the booked time was theirs
        db.delete(s)
        for oid in {ln.org_id for ln in db.scalars(select(PickupLine).where(
                PickupLine.pickup_id == p.id))}:
            notify_role(db, "business", "Collector changed",
                        f"Pickup #{p.id} has a new collector. "
                        "A new time will be confirmed.", org_id=oid)
    if C.DISPATCH_MODE == "solver":
        a.collector_id = None
        a.accepted_at = None
        db.flush()
        assign_set(db, [p] + _unaccepted(db, skip=p.id))
        return assignment_of(db, p.id)
    return assign_run(db, p, exclude=gone)


def settle(db, p):
    """Freeze the driver's fare when a run is closed."""
    a = assignment_of(db, p.id)
    if a and a.collector_id:
        a.fare_paise = fare_for(db, p, a.collector_id)["total_paise"]
        log_mark(db, p.id, a.collector_id, "closed_at")


# ---------- the trip log (recorded only; nothing reads it yet) ----------
def _open_log(db, pid, driver_id):
    return db.scalar(select(TripLog).where(
        TripLog.run_id == pid, TripLog.driver_id == driver_id,
        TripLog.declined_at.is_(None), TripLog.closed_at.is_(None))
        .order_by(TripLog.id.desc()))


def log_offer(db, p, driver_id, km):
    now = utcnow()
    local = now + IST
    db.add(TripLog(
        run_id=p.id, driver_id=driver_id, planned_km=km,
        planned_minutes=round(km / C.AVG_SPEED_KMH * 60, 1) if km else None,
        offered_at=now, stops=len(json.loads(p.route)),
        expected_kg=p.expected_kg, hour_of_day=local.hour,
        weekday=local.weekday()))
    db.flush()


def log_mark(db, pid, driver_id, field):
    """Stamp accepted_at / declined_at / started_at / closed_at on the
    driver's open log row for run `pid`."""
    row = _open_log(db, pid, driver_id)
    if not row or getattr(row, field):
        return
    now = utcnow()
    setattr(row, field, now)
    if field == "closed_at":
        p = db.get(Pickup, pid)
        row.hub_kg = p.hub_kg
        start = row.started_at or row.accepted_at or row.offered_at
        row.actual_minutes = round((now - start).total_seconds() / 60, 1)


# ---------- giving out many runs together ----------
def _unaccepted(db, skip=None):
    """Planned runs held by someone who has not said yes yet."""
    out = []
    for p in db.scalars(select(Pickup).where(Pickup.status == "planned")):
        a = assignment_of(db, p.id)
        if (p.id != skip and a and a.collector_id and not a.pending
                and not is_accepted(db, p)):
            out.append(p)
    return out


def _driver_pool(db, exclude_pids=()):
    busy = _open_counts(db, exclude_pids)
    return [O.Driver(u.id, (pr.base_lat, pr.base_lng), pr.capacity_kg,
                     busy.get(u.id, 0)) for pr, u in _live_profiles(db)]


def _run_of(db, p):
    a = assignment_of(db, p.id)
    fac = db.get(Facility, p.facility_id)
    return O.Run(p.id, p.expected_kg,
                 [(s["lat"], s["lng"]) for s in json.loads(p.route)],
                 (fac.lat, fac.lng),
                 set(json.loads(a.declined)) if a else set())


def _plan(db, pickups):
    """Run the solver over `pickups`; raises on any solver problem."""
    pids = [p.id for p in pickups]
    runs = [_run_of(db, p) for p in pickups]
    drivers = _driver_pool(db, pids)
    if not drivers:
        return O.Result({r.id: None for r in runs}, {},
                        {r.id: "no eligible driver" for r in runs}, 0.0,
                        "optimal")
    pts = [d.base for d in drivers] + [
        q for r in runs for q in (*r.stops, r.plant)]
    return O.solve(runs, drivers, Travel(pts))


def assign_set(db, pickups):
    """Give `pickups` to drivers all at once (solver). If the solver fails,
    each run falls back to the old nearest-driver rules. Returns a summary."""
    if not pickups:
        return {"runs": 0}
    try:
        res = _plan(db, pickups)
    except Exception as e:             # never leave runs stuck in a batch
        log.warning("solver failed, using rules: %s", e)
        for p in pickups:
            a = assignment_of(db, p.id)
            gone = set(json.loads(a.declined)) if a else set()
            assign_run(db, p, exclude=gone, note="fallback to rules: ")
        return {"runs": len(pickups), "status": "fallback",
                "error": str(e)[:200]}
    for p in pickups:
        _apply(db, p, res)
    db.flush()
    return {"runs": len(pickups), "status": res.status,
            "total_km": round(res.total_km, 1),
            "seconds": round(res.seconds, 3)}


def _apply(db, p, res):
    a = assignment_of(db, p.id)
    if not a:
        a = RunAssignment(pickup_id=p.id)
        db.add(a)
    new = res.assign.get(p.id)
    changed = new != a.collector_id or a.pending
    a.collector_id, a.pending = new, False
    a.reason = res.why.get(p.id, "")
    a.planned_km = res.km.get(p.id)
    if changed:
        a.accepted_at = None
        if new:
            log_offer(db, p, new, res.km[p.id])
            f = fare_for(db, p, new)
            notify(db, new, "New run assigned",
                   f"Run #{p.id}: {p.expected_kg:g} kg, {f['stops']} stop"
                   f"{'s' if f['stops'] != 1 else ''}, about "
                   f"Rs {f['total']:.0f} for the trip.", kind="info")


def record_shadow(db, pickups):
    """Shadow mode: note what the solver would have done, change nothing."""
    try:
        res = _plan(db, pickups)
    except Exception as e:
        log.warning("shadow solver failed: %s", e)
        return
    for p in pickups:
        a = assignment_of(db, p.id)
        if a:
            a.shadow_driver = res.assign.get(p.id)
            a.shadow_km = res.km.get(p.id)


def dispatch_new(db, created):
    """What happens to freshly planned runs, by DISPATCH_MODE."""
    if C.DISPATCH_MODE == "solver":
        for p in created:              # hold until the batch window closes
            a = assignment_of(db, p.id) or RunAssignment(pickup_id=p.id)
            a.pending, a.collector_id = True, None
            db.add(a)
        db.flush()
        if C.DISPATCH_BATCH_SECONDS <= 0:
            assign_batch(db, force=True)
        return
    for p in created:
        assign_run(db, p)
    if C.DISPATCH_MODE == "shadow":
        record_shadow(db, created)


def assign_batch(db, force=False):
    """Give out every run whose batch window has closed (all of them with
    force=True). Called by the background task and by the admin button."""
    cutoff = utcnow() - timedelta(seconds=C.DISPATCH_BATCH_SECONDS)
    q = select(RunAssignment).where(RunAssignment.pending)
    rows = [a for a in db.scalars(q) if force or a.assigned_at <= cutoff]
    pickups = [db.get(Pickup, a.pickup_id) for a in rows]
    out = assign_set(db, [p for p in pickups if p.status == "planned"])
    db.commit()
    return out
