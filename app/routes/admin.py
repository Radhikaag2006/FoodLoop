from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from ..clock import iso, utcnow
from ..db import get_db
from ..deps import need, notify_role
from ..models import Facility, Invite, Org, Pickup, Record, User
from ..security import clean, make_code, norm_phone
from .auth import issue_reset

router = APIRouter(prefix="/api/admin")
adm = need("admin")


@router.get("/overview")
def overview(db=Depends(get_db), u=Depends(adm)):
    roles = dict(db.execute(select(User.role, func.count()).where(
        User.status != "disabled",
        User.role.in_(("business", "hub", "admin"))).group_by(User.role)).all())
    kg = db.scalar(select(func.coalesce(func.sum(Pickup.hub_kg), 0))
                   .where(Pickup.status == "closed"))
    return {
        "users": roles,
        "orgs": db.query(Org).filter(Org.kind == "business").count(),
        "pending_orgs": db.query(Org).filter(
            Org.kind == "business",
            Org.verify_status == "pending").count(),
        "kg": round(float(kg or 0), 1),
        "pickups_open": db.query(Pickup).filter(
            Pickup.status.in_(("planned", "collected"))).count(),
        "records": db.query(Record).count(),
        "mismatches": db.query(Pickup).filter(
            Pickup.mismatch.is_(True)).count(),
    }


@router.get("/orgs")
def orgs(status: str = "pending", db=Depends(get_db), u=Depends(adm)):
    st = select(Org).where(Org.kind == "business").order_by(Org.id.desc())
    if status != "all":
        st = st.where(Org.verify_status == status)
    out = []
    for o in db.scalars(st.limit(100)):
        owner = db.scalar(select(User).where(
            User.org_id == o.id,
            User.role == "business"))
        out.append({"id": o.id, "name": o.name, "kind": o.kind,
                    "city": o.city, "address": o.address,
                    "fssai_no": o.fssai_no, "status": o.verify_status,
                    "business_type": o.business_type,
                    "owner": owner.name if owner else "",
                    "phone": owner.phone if owner else "",
                    "at": iso(o.created_at)})
    return out


@router.post("/orgs/{oid}/{act}")
def org_act(oid: int, act: str, db=Depends(get_db), u=Depends(adm)):
    o = db.get(Org, oid)
    if not o or act not in ("verify", "reject"):
        raise HTTPException(404, "Organisation not found.")
    o.verify_status = "verified" if act == "verify" else "rejected"
    notify_role(
        db, "business",
        "You're verified" if act == "verify" else "Verification declined",
        "Pickups can now be planned for you." if act == "verify"
        else "Please contact FoodLoop support.", org_id=o.id,
        kind="info" if act == "verify" else "warn")
    db.commit()
    return {"ok": True}


class FacIn(BaseModel):
    name: str
    kind: str
    tiers: str
    lat: float
    lng: float
    capacity_kg: float
    certified: bool = False
    cert_no: str = ""
    address: str = ""
    phone: str = ""
    rate_per_kg: float = 0.0


def _fac_dict(f):
    return {"id": f.id, "name": f.name, "kind": f.kind, "tiers": f.tiers,
            "lat": f.lat, "lng": f.lng, "capacity_kg": f.capacity_kg,
            "certified": f.certified, "cert_no": f.cert_no,
            "address": f.address, "phone": f.phone,
            "rate_per_kg": f.rate_per_kg, "active": f.active}


def _fill(f, b):
    tiers = "".join(sorted(set(b.tiers.upper()) & set("ABCDE")))
    if not tiers:
        raise HTTPException(422, "Pick at least one tier.")
    if ("D" in tiers or "E" in tiers) and not (
            b.certified and b.cert_no.strip()):
        raise HTTPException(
            422, "Compost, digestion and recycling need a certificate "
                 "number.")
    f.name, f.kind = clean(b.name, 120, "Name"), b.kind[:20]
    f.tiers, f.lat, f.lng = tiers, b.lat, b.lng
    f.capacity_kg = max(0, b.capacity_kg)
    f.certified, f.cert_no = b.certified, b.cert_no.strip()[:40]
    f.address = b.address.strip()[:200]
    f.phone = norm_phone(b.phone) if b.phone.strip() else ""
    f.rate_per_kg = b.rate_per_kg


@router.get("/facilities")
def facilities(db=Depends(get_db), u=Depends(adm)):
    return [_fac_dict(f) for f in db.scalars(
        select(Facility).order_by(Facility.id))]


@router.post("/facilities")
def add_fac(b: FacIn, db=Depends(get_db), u=Depends(adm)):
    f = Facility()
    _fill(f, b)
    db.add(f)
    db.commit()
    return _fac_dict(f)


@router.put("/facilities/{fid}")
def edit_fac(fid: int, b: FacIn, db=Depends(get_db), u=Depends(adm)):
    f = db.get(Facility, fid)
    if not f:
        raise HTTPException(404, "Facility not found.")
    _fill(f, b)
    db.commit()
    return _fac_dict(f)


@router.post("/facilities/{fid}/toggle")
def toggle_fac(fid: int, db=Depends(get_db), u=Depends(adm)):
    f = db.get(Facility, fid)
    if not f:
        raise HTTPException(404, "Facility not found.")
    f.active = not f.active
    db.commit()
    return _fac_dict(f)


class InvIn(BaseModel):
    note: str = ""


@router.post("/invites")
def invite(b: InvIn, db=Depends(get_db), u=Depends(adm)):
    for _ in range(10):
        c = make_code(8)
        if not db.query(Invite).filter(Invite.code == c).first():
            break
    db.add(Invite(code=c, role="hub", note=b.note.strip()[:80],
                  created_by=u.id,
                  expires_at=utcnow() + timedelta(days=7)))
    db.commit()
    return {"code": c}


@router.get("/invites")
def invites(db=Depends(get_db), u=Depends(adm)):
    rows = db.scalars(select(Invite).where(
        Invite.role == "hub", Invite.used_by.is_(None),
        Invite.expires_at > utcnow())).all()
    return [{"id": i.id, "code": i.code, "note": i.note,
             "expires": iso(i.expires_at)} for i in rows]


@router.get("/users")
def users(q: str = "", db=Depends(get_db), u=Depends(adm)):
    st = select(User).where(User.role.in_(("business", "hub", "admin"))
                           ).order_by(User.id.desc())
    q = q.strip()
    if q:
        like = f"%{q}%"
        st = st.where(or_(User.name.ilike(like), User.phone.like(like),
                          User.email.ilike(like)))
    out = []
    for r in db.scalars(st.limit(50)):
        o = db.get(Org, r.org_id) if r.org_id else None
        out.append({"id": r.id, "name": r.name, "phone": r.phone,
                    "email": r.email, "role": r.role, "status": r.status,
                    "org": o.name if o else ""})
    return out


@router.post("/users/{uid}/{act}")
def user_act(uid: int, act: str, db=Depends(get_db), u=Depends(adm)):
    t = db.get(User, uid)
    if not t or t.role == "admin":
        raise HTTPException(404, "Person not found.")
    if act == "disable":
        t.status, t.sv = "disabled", t.sv + 1
    elif act == "enable":
        t.status = "active"
    elif act == "reset-code":
        code = issue_reset(db, t)
        db.commit()
        return {"code": code, "phone": t.phone, "minutes": 30}
    else:
        raise HTTPException(422, "Unknown action.")
    db.commit()
    return {"ok": True}


@router.get("/records")
def records(db=Depends(get_db), u=Depends(adm)):
    rows = db.scalars(select(Record).order_by(Record.id.desc())
                      .limit(50)).all()
    return [{"code": r.code, "at": iso(r.created_at)} for r in rows]
