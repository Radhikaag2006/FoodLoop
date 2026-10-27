import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from .. import config as C
from ..clock import utcnow
from ..db import get_db
from ..deps import (any_user, user_dict, notify_role, session_user)
from ..mailer import send_mail
from ..models import User, Org, Invite, ResetCode, Notification
from ..security import (hash_pw, check_pw, check_strength, norm_phone,
                        norm_email, clean, make_code,
                        hash_code, rate_limit)

router = APIRouter(prefix="/api/auth")


def _ip(request):
    return request.client.host if request.client else "x"


def _login(request, u):
    request.session.clear()
    request.session["uid"] = u.id
    request.session["sv"] = u.sv


class SignupIn(BaseModel):
    role: str
    name: str
    phone: str
    email: str = ""
    password: str
    # hub (pickup person): needs an invite from the admin
    invite_code: str = ""
    # business
    org_name: str = ""
    business_type: str = ""
    fssai_no: str = ""
    address: str = ""
    city: str = ""
    lat: float | None = None
    lng: float | None = None


def _place(b):
    lat, lng = b.lat, b.lng
    if lat is None or lng is None or not (
            -90 <= lat <= 90 and -180 <= lng <= 180):
        if b.city not in C.CITIES:
            raise HTTPException(
                422, "Choose your city or share your location.")
        lat, lng = C.CITIES[b.city]
    return lat, lng


@router.post("/signup")
def signup(b: SignupIn, request: Request, db=Depends(get_db)):
    rate_limit("signup:" + _ip(request), 10, 3600)
    if b.role not in ("business", "hub"):
        raise HTTPException(422, "Choose how you will use FoodLoop.")
    name = clean(b.name, 80, "Your name")
    phone = norm_phone(b.phone)
    email = norm_email(b.email) if b.email.strip() else None
    check_strength(b.password)
    if db.scalar(select(User).where(User.phone == phone)):
        raise HTTPException(
            409, "This mobile number already has an account. Sign in instead.")
    if email and db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            409, "This email already has an account. Sign in instead.")

    u = User(name=name, phone=phone, email=email, role=b.role,
             pw_hash=hash_pw(b.password), status="active")
    try:
        if b.role == "hub":
            inv = db.scalar(select(Invite).where(
                Invite.code == (b.invite_code or "").strip().upper()))
            if (not inv or inv.role != "hub"
                    or inv.expires_at < utcnow()):
                raise HTTPException(
                    422, "This invite code is invalid or has expired.")
            u.org_id = inv.org_id
        else:
            oname = clean(b.org_name, 120, "Name")
            lat, lng = _place(b)
            org = Org(name=oname, lat=lat, lng=lng, kind="business",
                      address=clean(b.address, 200, "Address"),
                      city=b.city[:40], contact_phone=phone,
                      business_type=b.business_type[:30],
                      fssai_no=b.fssai_no.strip()[:20])
            db.add(org)
            db.flush()
            u.org_id = org.id
        db.add(u)
        db.flush()
        if b.role == "hub":              # a code works until it expires
            inv.used_by, inv.uses = u.id, (inv.uses or 0) + 1
        else:
            notify_role(db, "admin", "New business to verify",
                        f"{org.name} signed up.", kind="approval")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That account already exists.")
    except HTTPException:
        db.rollback()
        raise
    _login(request, u)
    return user_dict(db, u)


@router.get("/invite/{code}")
def invite_info(code: str, request: Request, db=Depends(get_db)):
    rate_limit("invite:" + _ip(request), 30, 600)
    inv = db.scalar(select(Invite).where(
        Invite.code == code.strip().upper()))
    if not inv or inv.expires_at < utcnow():
        raise HTTPException(
            404, "This invite code is invalid or has expired.")
    org = db.get(Org, inv.org_id) if inv.org_id else None
    return {"role": inv.role, "org": org.name if org else "FoodLoop"}


class LoginIn(BaseModel):
    identifier: str
    password: str


@router.post("/login")
def login(b: LoginIn, request: Request, db=Depends(get_db)):
    ident = b.identifier.strip().lower()
    rate_limit("login-ip:" + _ip(request), 30, 600)
    rate_limit("login-id:" + ident, 8, 600)
    u = None
    if "@" in ident:
        u = db.scalar(select(User).where(User.email == ident))
    else:
        try:
            u = db.scalar(select(User).where(
                User.phone == norm_phone(ident)))
        except HTTPException:
            u = None
    if not u or not check_pw(b.password, u.pw_hash):
        raise HTTPException(401, "Wrong mobile, email or password.")
    if u.status == "disabled":
        raise HTTPException(403, "This account has been turned off.")
    if u.role not in ("business", "hub", "admin"):
        raise HTTPException(403, "This account type is no longer in use.")
    u.last_login = utcnow()
    db.commit()
    _login(request, u)
    return user_dict(db, u)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request, db=Depends(get_db)):
    u = session_user(request, db)
    return {"user": user_dict(db, u) if u else None}


class ProfileIn(BaseModel):
    name: str
    email: str = ""
    phone: str


@router.put("/profile")
def profile(b: ProfileIn, db=Depends(get_db), u=Depends(any_user)):
    u.name = clean(b.name, 80, "Your name")
    phone = norm_phone(b.phone)
    email = norm_email(b.email) if b.email.strip() else None
    for col, val in (("phone", phone), ("email", email)):
        if val:
            other = db.scalar(select(User).where(
                getattr(User, col) == val, User.id != u.id))
            if other:
                raise HTTPException(409, f"That {col} is already in use.")
    u.phone, u.email = phone, email
    db.commit()
    return user_dict(db, u)


class PwIn(BaseModel):
    old_password: str
    new_password: str


@router.post("/password")
def change_pw(b: PwIn, request: Request, db=Depends(get_db),
              u=Depends(any_user)):
    rate_limit(f"pw:{u.id}", 6, 600)
    if not check_pw(b.old_password, u.pw_hash):
        raise HTTPException(403, "Your current password is wrong.")
    check_strength(b.new_password)
    u.pw_hash = hash_pw(b.new_password)
    u.sv += 1                        # signs out every other device
    db.commit()
    _login(request, u)
    return {"ok": True}


class DelIn(BaseModel):
    password: str


@router.post("/delete")
def delete_account(b: DelIn, request: Request, db=Depends(get_db),
                   u=Depends(any_user)):
    if not check_pw(b.password, u.pw_hash):
        raise HTTPException(403, "Your password is wrong.")
    if u.role == "admin":
        raise HTTPException(403, "Admin accounts can't be deleted here.")
    u.name, u.email, u.phone = "Deleted user", None, None
    u.status, u.sv = "disabled", u.sv + 1
    u.pw_hash = hash_pw(secrets.token_hex(16))
    db.commit()
    request.session.clear()
    return {"ok": True}


# ---------- password reset ----------
def issue_reset(db, user) -> str:
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    db.add(ResetCode(user_id=user.id, code_hash=hash_code(code),
                     expires_at=utcnow() + timedelta(minutes=30)))
    return code


class ForgotIn(BaseModel):
    identifier: str


@router.post("/forgot")
def forgot(b: ForgotIn, request: Request, db=Depends(get_db)):
    ident = b.identifier.strip().lower()
    rate_limit("forgot-ip:" + _ip(request), 10, 3600)
    rate_limit("forgot-id:" + ident, 3, 3600)
    u = None
    try:
        if "@" in ident:
            u = db.scalar(select(User).where(User.email == ident))
        else:
            u = db.scalar(select(User).where(
                User.phone == norm_phone(ident)))
    except HTTPException:
        pass
    out = {"ok": True, "message": (
        "If this account exists and has an email, we sent a 6-digit "
        "code. Otherwise ask the FoodLoop team for a "
        "reset code.")}
    if u and u.status in ("active", "pending"):
        code = issue_reset(db, u)
        db.commit()
        if u.email:
            send_mail(u.email, "Your FoodLoop reset code",
                      f"Your code is {code}. It works for 30 minutes.")
        if not C.IS_PROD:
            out["dev_code"] = code
    return out


class ResetIn(BaseModel):
    identifier: str
    code: str
    new_password: str


@router.post("/reset")
def reset(b: ResetIn, request: Request, db=Depends(get_db)):
    ident = b.identifier.strip().lower()
    rate_limit("reset-ip:" + _ip(request), 20, 3600)
    bad = HTTPException(422, "That code is wrong or has expired.")
    try:
        u = db.scalar(select(User).where(
            User.email == ident if "@" in ident
            else User.phone == norm_phone(ident)))
    except HTTPException:
        raise bad
    if not u:
        raise bad
    check_strength(b.new_password)
    rc = db.scalar(select(ResetCode).where(
        ResetCode.user_id == u.id, ResetCode.used.is_(False),
        ResetCode.expires_at > utcnow()).order_by(ResetCode.id.desc()))
    if not rc or rc.attempts >= 5:
        raise bad
    if hash_code(b.code.strip()) != rc.code_hash:
        rc.attempts += 1
        db.commit()
        raise bad
    rc.used = True
    u.pw_hash = hash_pw(b.new_password)
    u.sv += 1
    db.commit()
    return {"ok": True}


# ---------- notifications ----------
@router.get("/notifications")
def notifications(db=Depends(get_db), u=Depends(any_user)):
    rows = db.scalars(select(Notification).where(
        Notification.user_id == u.id)
        .order_by(Notification.id.desc()).limit(40)).all()
    return [{"id": n.id, "title": n.title, "body": n.body,
             "kind": n.kind, "read": n.read,
             "at": n.created_at.isoformat()} for n in rows]


@router.post("/notifications/read")
def read_all(db=Depends(get_db), u=Depends(any_user)):
    db.query(Notification).filter(
        Notification.user_id == u.id).update({"read": True})
    db.commit()
    return {"ok": True}
