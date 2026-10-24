import json
from math import radians, sin, cos, asin, sqrt

from sqlalchemy import select

from .models import Facility, Org, Pickup, PickupLine, Lot
from .config import MIN_PICKUP_KG


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


def plan_pickups(db, min_kg=None):
    """Group pending items by best facility; plan a run only when the
    group reaches the minimum volume (route-density rule)."""
    min_kg = MIN_PICKUP_KG if min_kg is None else min_kg
    pending = []
    for lot in db.scalars(select(Lot).where(Lot.pickup_id.is_(None))):
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

    created, waiting = [], []
    for fid, rows in groups.items():
        total = sum(r[2] for r in rows)
        fac = db.get(Facility, fid)
        if total < min_kg:
            waiting.append({"facility": fac.name,
                            "kg": round(total, 1), "need": min_kg})
            continue
        orgs = {r[3].id: r[3] for r in rows}.values()
        stops, km, last = _order_stops(orgs, (fac.lat, fac.lng))
        per = {}
        for r in rows:
            per[r[3].id] = per.get(r[3].id, 0) + r[2]
        for st in stops:
            st["kg"] = round(per.get(st["org_id"], 0), 1)
        km += haversine(last[0], last[1], fac.lat, fac.lng)
        p = Pickup(facility_id=fid, expected_kg=round(total, 2),
                   route_km=round(km, 1), route=json.dumps(stops))
        db.add(p)
        db.flush()
        for kind, obj, kg, org in rows:
            db.add(PickupLine(
                pickup_id=p.id, org_id=org.id, ref_type=kind,
                ref_id=obj.id, kg=kg, tier=obj.tier))
            obj.pickup_id = p.id
        created.append(p)
    db.commit()
    return created, waiting
