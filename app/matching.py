import json
from math import radians, sin, cos, asin, sqrt

from sqlalchemy import select

from .models import Facility, Org, Pickup, PickupLine, Lot
from .config import CLUB_MAX_KM, MIN_PICKUP_KG
from .tiers import TIERS


def haversine(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = p2 - p1
    dl = radians(lng2 - lng1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * asin(sqrt(a))


def rank_facilities(db, tier, lat, lng, kg, limit=3):
    """Rank facilities for a tier by distance, capacity and price."""
    rows = db.scalars(select(Facility).where(Facility.active)).all()
    out = []
    for f in rows:
        if tier not in f.tiers:
            continue
        if tier in ("D", "E") and not f.certified:
            continue
        d = haversine(lat, lng, f.lat, f.lng)
        s_dist = 1 / (1 + d / 10)
        s_cap = min(1.0, f.capacity_kg / max(kg, 1))
        s_price = max(0.0, min(1.0, (f.rate_per_kg + 5) / 10))
        score = 0.5 * s_dist + 0.2 * s_cap + 0.3 * s_price
        out.append({
            "facility": f,
            "distance_km": round(d, 1),
            "score": round(score, 3),
            "est_value": round(f.rate_per_kg * kg, 2),
        })
    out.sort(key=lambda r: r["score"], reverse=True)
    return out[:limit]


def facility_dict(r):
    f = r["facility"]
    return {
        "id": f.id, "name": f.name, "kind": f.kind,
        "lat": f.lat, "lng": f.lng, "certified": f.certified,
        "rate_per_kg": f.rate_per_kg,
        "distance_km": r["distance_km"],
        "score": r["score"], "est_value": r["est_value"],
    }


def _order_stops(orgs, start):
    """Nearest-neighbour ordering of stops; returns (stops, km)."""
    left = list(orgs)
    cur = start
    stops, km = [], 0.0
    while left:
        nxt = min(left, key=lambda o: haversine(
            cur[0], cur[1], o.lat, o.lng))
        km += haversine(cur[0], cur[1], nxt.lat, nxt.lng)
        stops.append({"org_id": nxt.id, "name": nxt.name,
                      "lat": nxt.lat, "lng": nxt.lng,
                      "address": nxt.address,
                      "phone": nxt.contact_phone,
                      "point": nxt.collection_point})
        cur = (nxt.lat, nxt.lng)
        left.remove(nxt)
    return stops, km, cur


def split_by_capacity(rows, fac, cap_kg):
    """Cut one plant's lots into vehicle-sized loads.

    Lots are taken in driving order (nearest stop first, starting from the
    plant) and a new load starts when the next lot would overfill the
    vehicle. A single lot bigger than the vehicle gets a load of its own."""
    if not cap_kg or sum(r[2] for r in rows) <= cap_kg:
        return [rows]
    orgs = {r[3].id: r[3] for r in rows}.values()
    order = [st["org_id"] for st in _order_stops(
        orgs, (fac.lat, fac.lng))[0]]
    loads, used = [[]], 0.0
    for oid in order:
        for r in (x for x in rows if x[3].id == oid):
            if loads[-1] and used + r[2] > cap_kg:
                loads.append([])
                used = 0.0
            loads[-1].append(r)
            used += r[2]
    return loads


def _make_run(db, fac, rows):
    orgs = {r[3].id: r[3] for r in rows}.values()
    stops, km, last = _order_stops(orgs, (fac.lat, fac.lng))
    per = {}
    for r in rows:
        per[r[3].id] = per.get(r[3].id, 0) + r[2]
    for st in stops:
        st["kg"] = round(per.get(st["org_id"], 0), 1)
    km += haversine(last[0], last[1], fac.lat, fac.lng)
    p = Pickup(facility_id=fac.id, expected_kg=round(sum(r[2] for r in rows), 2),
               route_km=round(km, 1), route=json.dumps(stops))
    db.add(p)
    db.flush()
    for kind, obj, kg, org in rows:
        db.add(PickupLine(
            pickup_id=p.id, org_id=org.id, ref_type=kind,
            ref_id=obj.id, kg=kg, tier=obj.tier))
        obj.pickup_id = p.id
    return p


def _club_target(db, rows, big):
    """Nearest viable run (facility id) that can take every lot in `rows`
    and is within CLUB_MAX_KM of the closest stop, or None."""
    best, best_d = None, None
    for fid in big:
        fac = db.get(Facility, fid)
        if not all(r[1].tier in fac.tiers and (
                r[1].tier not in ("D", "E") or fac.certified) for r in rows):
            continue
        d = min(haversine(r[3].lat, r[3].lng, fac.lat, fac.lng)
                for r in rows)
        if d <= CLUB_MAX_KM and (best_d is None or d < best_d):
            best, best_d = fid, d
    return best


def plan_pickups(db, min_kg=None, cap_kg=None):
    """Group pending items by best facility. A group that reaches the
    minimum volume gets its own run; a smaller one is clubbed into the
    nearest such run that can take it, and only waits if there is none.
    With `cap_kg` (the biggest vehicle) a big run is split into several."""
    min_kg = MIN_PICKUP_KG if min_kg is None else min_kg
    pending = []
    for lot in db.scalars(select(Lot).where(Lot.pickup_id.is_(None))):
        if lot.tier not in TIERS:      # retired rescue lots are not collected
            continue
        pending.append(("lot", lot, lot.qty_kg))

    groups = {}
    for kind, obj, kg in pending:
        org = db.get(Org, obj.org_id)
        if org.verify_status != "verified":
            continue
        ranked = rank_facilities(db, obj.tier, org.lat, org.lng, kg, 1)
        if not ranked:
            continue
        fid = ranked[0]["facility"].id
        groups.setdefault(fid, []).append((kind, obj, kg, org))

    big = {f: r for f, r in groups.items() if sum(x[2] for x in r) >= min_kg}
    small = {f: r for f, r in groups.items() if f not in big}
    waiting = []
    for fid, rows in small.items():
        target = _club_target(db, rows, big)
        if target:                      # ride along with a bigger run
            big[target].extend(rows)
        else:
            waiting.append({"facility": db.get(Facility, fid).name,
                            "kg": round(sum(r[2] for r in rows), 1),
                            "need": min_kg})

    created = []
    for fid, rows in big.items():
        fac = db.get(Facility, fid)
        for load in split_by_capacity(rows, fac, cap_kg):
            created.append(_make_run(db, fac, load))
    db.commit()
    return created, waiting
