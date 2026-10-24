from fastapi import Depends, HTTPException, Request

from .db import get_db
from .models import User, Org, Notification


LIVE_ROLES = ("business", "hub", "admin")


def session_user(request: Request, db):
    uid = request.session.get("uid")
    if not uid:
        return None
    u = db.get(User, uid)
    if not u or u.sv != request.session.get("sv"):
        request.session.clear()
        return None
    if u.status in ("disabled", "rejected") or u.role not in LIVE_ROLES:
        request.session.clear()
        return None
    return u


def any_user(request: Request, db=Depends(get_db)):
    u = session_user(request, db)
    if not u:
        raise HTTPException(401, "Please sign in to continue.")
    return u


def current_user(u=Depends(any_user)):
    if u.status != "active":
        raise HTTPException(403, "Your account is waiting for approval.")
    return u


def need(*roles):
    def dep(u=Depends(current_user)):
        if u.role not in roles:
            raise HTTPException(403, "This isn't available for your account.")
        return u
    return dep


def user_dict(db, u, secrets=False):
    out = {"id": u.id, "name": u.name, "email": u.email or "",
           "phone": u.phone or "", "role": u.role, "status": u.status}
    if u.org_id:
        o = db.get(Org, u.org_id)
        out["org"] = {"id": o.id, "name": o.name, "kind": o.kind,
                      "verify_status": o.verify_status, "city": o.city,
                      "address": o.address, "schedule": o.schedule,
                      "collection_point": o.collection_point,
                      "fssai_no": o.fssai_no,
                      "business_type": o.business_type}
    out["unread"] = db.query(Notification).filter(
        Notification.user_id == u.id, Notification.read.is_(False)).count()
    return out


def notify(db, user_id, title, body="", kind="info"):
    db.add(Notification(user_id=user_id, title=title[:100],
                        body=body[:240], kind=kind))


def notify_role(db, role, title, body="", org_id=None, kind="info"):
    q = db.query(User).filter(User.role == role, User.status == "active")
    if org_id:
        q = q.filter(User.org_id == org_id)
    for u in q.all():
        notify(db, u.id, title, body, kind)
