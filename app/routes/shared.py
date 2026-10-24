import json

from sqlalchemy import select

from ..clock import iso
from ..models import Facility, Org, Record


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
