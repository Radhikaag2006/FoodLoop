"""First-run setup.

bootstrap(): creates the platform admin from ADMIN_EMAIL/ADMIN_PASSWORD.
seed_demo(): FICTIONAL businesses, facilities and lots (only when
DEMO_MODE=1). Never use demo data for real
users. Demo password for every demo account: Demo@1234
"""
import logging
import sys
from datetime import timedelta, date

from sqlalchemy import or_, select

from . import config as C
from .clock import utcnow
from .db import Base, engine, SessionLocal
from .matching import plan_pickups
from .models import CollectorProfile, Org, User, Facility, Lot
from .records import create_record
from .billing import ensure_plans
from .security import check_pw, hash_pw
from .tiers import classify

log = logging.getLogger("foodloop")

DEMO_PW = "Demo@1234"
FACILITIES = [
    # name, kind, tiers, lat, lng, cap, certified, rate, cert
    ("Demo Pulp and Pickle Unit", "processor", "B", 28.469, 77.530,
     500, False, 4.0, ""),
    ("Demo Pulp Unit 2, Noida", "processor", "B", 28.620, 77.380,
     400, False, 3.5, ""),
    ("Demo Feed Mill, Dadri", "feed", "C", 28.548, 77.550,
     2000, False, 1.5, ""),
    ("Demo Cattle-feed Co-op", "feed", "C", 28.590, 77.425,
     1000, False, 1.0, ""),
    ("Demo Compost Unit, Surajpur", "compost", "D", 28.459, 77.520,
     3000, True, -1.5, "DEMO-C-001"),
    ("Demo Biogas Plant, Dadri", "biogas", "D", 28.560, 77.570,
     10000, True, -1.0, "DEMO-B-002"),
    ("Demo Anaerobic Digester, Noida", "biogas", "D", 28.580, 77.350,
     5000, True, -2.0, "DEMO-B-003"),
    ("Demo Packaging Recycler", "recycler", "E", 28.660, 77.440,
     2000, True, 2.0, "DEMO-R-004"),
]


def reset():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _public_password(pw):
    """True when `pw` is the published demo password on a production site."""
    return C.IS_PROD and pw == DEMO_PW


def disable_demo_accounts(db):
    """Production only. Demo users (phones 9000000xxx, admin@foodloop.local)
    that still have the published demo password are an open door, so turn
    them off. Accounts whose owner changed the password are left alone."""
    off = 0
    rows = db.scalars(select(User).where(or_(
        User.phone.like("9000000%"), User.email == "admin@foodloop.local")))
    for u in rows:
        if u.status != "disabled" and check_pw(DEMO_PW, u.pw_hash):
            u.status = "disabled"
            u.sv = (u.sv or 1) + 1               # signs out open sessions
            off += 1
    if off:
        db.commit()
        log.warning("Turned off %d demo account(s) that still had the "
                    "public demo password.", off)
    return off


def _admin_ready(db, admin, email, pw):
    """What to do when an admin already exists: say which one, and reset it
    when asked. Returns nothing; every outcome is logged so a wrong login
    on a live site can be explained from the logs."""
    if not (email and pw):
        log.info("Admin account: %s", admin.email)
        return
    email = email.lower()
    if _public_password(pw):
        log.error("ADMIN_PASSWORD is the public demo password. Choose a "
                  "different one; the admin was not changed.")
        return
    same = admin.email == email and check_pw(pw, admin.pw_hash)
    if C.ADMIN_PASSWORD_RESET:
        clash = db.scalar(select(User).where(
            User.email == email, User.id != admin.id))
        if clash:
            log.error("Admin reset skipped: %s belongs to another account.",
                      email)
            return
        admin.email, admin.pw_hash, admin.status = email, hash_pw(pw), "active"
        admin.sv = (admin.sv or 1) + 1           # signs out old sessions
        db.commit()
        log.warning("Admin reset: sign in as %s with ADMIN_PASSWORD. Remove "
                    "ADMIN_PASSWORD_RESET now.", email)
    elif same:
        log.info("Admin account: %s (matches ADMIN_EMAIL / ADMIN_PASSWORD)",
                 admin.email)
    else:
        log.warning("An admin already exists (%s) and does not match "
                    "ADMIN_EMAIL / ADMIN_PASSWORD, which are only used when "
                    "there is no admin. Set ADMIN_PASSWORD_RESET=1 for one "
                    "deploy to reset it.", admin.email)


def bootstrap():
    db = SessionLocal()
    try:
        email, pw = C.ADMIN_EMAIL, C.ADMIN_PASSWORD
        admin = db.scalar(select(User).where(User.role == "admin"))
        if admin:
            return _admin_ready(db, admin, email, pw)
        if not (email and pw):
            if C.IS_PROD:
                log.warning("No admin yet. Set ADMIN_EMAIL and "
                            "ADMIN_PASSWORD, then restart.")
                return
            email, pw = "admin@foodloop.local", DEMO_PW
            log.warning("Dev admin created: %s / %s", email, pw)
        if _public_password(pw):
            log.error("ADMIN_PASSWORD is the public demo password. Choose a "
                      "different one; no admin was created.")
            return
        db.add(User(name="FoodLoop Admin", email=email.lower(),
                    role="admin", pw_hash=hash_pw(pw)))
        db.commit()
        log.info("Admin created: %s", email.lower())
    finally:
        db.close()


def _user(db, name, phone, role, org=None):
    u = User(name=name, phone=phone, role=role, status="active",
             org_id=org.id if org else None, pw_hash=hash_pw(DEMO_PW))
    db.add(u)
    db.flush()
    return u


def seed_demo():
    db = SessionLocal()
    try:
        if db.scalars(select(Org)).first():
            return
        dist = Org(name="Demo Distributors Pvt Ltd", kind="business",
                   business_type="distributor", fssai_no="DEMO-FSSAI-1",
                   lat=28.530, lng=77.400, city="Greater Noida",
                   address="Ecotech, Greater Noida (demo)",
                   contact_phone="9000000005", verify_status="verified")
        mfg = Org(name="Demo Foods Manufacturing", kind="business",
                  business_type="manufacturer", fssai_no="",
                  lat=28.510, lng=77.540, city="Greater Noida",
                  address="Surajpur (demo)", contact_phone="9000000006",
                  verify_status="pending")
        db.add_all([dist, mfg])
        db.flush()
        for f in FACILITIES:
            db.add(Facility(name=f[0], kind=f[1], tiers=f[2], lat=f[3],
                            lng=f[4], capacity_kg=f[5], certified=f[6],
                            rate_per_kg=f[7], cert_no=f[8],
                            address="Demo address", phone=""))
        _user(db, "Rohit Gupta", "9000000005", "business", dist)
        _user(db, "Neha Singh", "9000000006", "business", mfg)
        imran = _user(db, "Imran Khan", "9000000007", "hub")
        db.add(CollectorProfile(
            user_id=imran.id, vehicle="Tata Ace (demo)", capacity_kg=500,
            base_lat=28.474, base_lng=77.504, base_label="Greater Noida"))

        today = date.today()
        for org, item, cond, kg, days in (
                (dist, "snacks", "fresh", 40, -20),
                (dist, "dairy", "fresh", 25, -3),
                (dist, "bakery", "fresh", 15, -5),
                (mfg, "cooked", "fresh", 30, -10)):
            exp = today + timedelta(days=days)
            t = classify(item, cond, expiry=exp)
            db.add(Lot(org_id=org.id, item=item, condition=cond,
                       qty_kg=kg, expiry=exp, tier=t["tier"],
                       created_at=utcnow() - timedelta(days=9)))
        db.commit()
        # close one older run so Records and the audit trail have data
        created, _ = plan_pickups(db, 5)
        for p in created[:2]:
            p.status, p.closed_at = "closed", utcnow() - timedelta(days=6)
            p.hub_kg = round(p.expected_kg * 1.01, 1)
            p.facility_kg = round(p.expected_kg * 1.0, 1)
            db.flush()
            create_record(db, p)
        db.add(Lot(org_id=dist.id, item="dairy", condition="fresh",
                   qty_kg=18, expiry=today - timedelta(days=2),
                   tier="D"))
        db.commit()
    finally:
        db.close()


def ensure_columns():
    """create_all adds tables but never columns: add the ones we grew."""
    from sqlalchemy import inspect, text
    have = {c["name"] for c in inspect(engine).get_columns("invoices")}
    if "breakdown" not in have:
        with engine.begin() as cx:
            cx.execute(text(
                "ALTER TABLE invoices ADD COLUMN breakdown TEXT DEFAULT '[]'"))
    have = {c["name"] for c in inspect(engine).get_columns("run_assignments")}
    if "accepted_at" not in have:
        with engine.begin() as cx:
            cx.execute(text(
                "ALTER TABLE run_assignments ADD COLUMN accepted_at DATETIME"))


def init():
    Base.metadata.create_all(engine)
    ensure_columns()
    bootstrap()
    db = SessionLocal()
    try:
        if C.IS_PROD:
            disable_demo_accounts(db)
        ensure_plans(db)
    finally:
        db.close()
    if C.DEMO_MODE:
        seed_demo()


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset()
    if "--demo" in sys.argv:
        if C.IS_PROD:
            sys.exit("Demo data is never loaded in production.")
        C.DEMO_MODE = True
    init()
    print("Done.")
