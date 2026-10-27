import json

from sqlalchemy import select

from datetime import timedelta

from ..clock import iso
from ..models import (Facility, FacilityDoc, Org, PickupSchedule, Record,
                      RunAssignment, User)

WINDOW = timedelta(hours=2)


def schedule_dict(db, pickup_id):
    """Who will collect a pickup and when. starts/ends are None until the
    collector confirms a time; None overall while nobody has the run."""
    s = db.scalar(select(PickupSchedule).where(
        PickupSchedule.pickup_id == pickup_id))
    a = db.scalar(select(RunAssignment).where(
        RunAssignment.pickup_id == pickup_id))
    cid = (a.collector_id if a and a.collector_id else None) or (
        s.collector_id if s else None)
    if not cid:
        return None
    c = db.get(User, cid)
    return {"starts": iso(s.starts_at) if s else None,
            "ends": iso(s.starts_at + WINDOW) if s else None,
            "collector": {"name": c.name, "phone": c.phone or ""}}


def facility_card(db, f, distance_km=None):
    """What a business may see about a plant. No prices or fees."""
    return {"id": f.id, "name": f.name, "kind": f.kind,
            "address": f.address, "lat": f.lat, "lng": f.lng,
            "certified": f.certified, "cert_no": f.cert_no,
            "has_document": bool(db.scalar(select(FacilityDoc.id).where(
                FacilityDoc.facility_id == f.id))),
            "distance_km": distance_km}


def pickup_dict(db, p):
    fac = db.get(Facility, p.facility_id)
    rec = db.scalar(select(Record).where(Record.pickup_id == p.id))
    return {
        "id": p.id, "status": p.status, "facility": fac.name,
        "facility_kind": fac.kind, "certified": fac.certified,
        "facility_address": fac.address, "facility_phone": fac.phone,
        "expected_kg": p.expected_kg, "hub_kg": p.hub_kg,
        "facility_kg": p.facility_kg, "mismatch": p.mismatch,
        "route_km": p.route_km, "route": json.loads(p.route),
        "fac_lat": fac.lat, "fac_lng": fac.lng,
        "record": rec.code if rec else "",
        "created_at": iso(p.created_at), "closed_at": iso(p.closed_at),
        "schedule": schedule_dict(db, p.id),
    }


def csv_response(rows, filename):
    import csv
    import io
    from fastapi.responses import Response
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return Response(
        buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="{filename}"'})


def org_of(db, user):
    return db.get(Org, user.org_id)
