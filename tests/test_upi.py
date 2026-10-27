import json
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from app import billing as B
from app import config as C
from app import dispatch as D
from app import payments as P
from app.db import SessionLocal
from app.models import (CollectorProfile, Facility, Invoice, Pickup,
                        PickupLine, Plan, User)
from app.security import hash_pw
from conftest import login

PW = "Strong123"


def _signup(c, phone, name):
    c.cookies.clear()
    r = c.post("/api/auth/signup", json={
        "role": "business", "name": name, "phone": phone, "password": PW,
        "org_name": name + " Foods", "address": "Sector 1", "city": "Noida"})
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        return db.scalar(select(User).where(User.phone == phone)).org_id
    finally:
        db.close()


def _closed_run(org_id, kg=40.0, tier="D", collector=None):
    db = SessionLocal()
    try:
        fid = db.scalars(select(Facility.id)).first()
        p = Pickup(facility_id=fid, status="closed", expected_kg=kg,
                   hub_kg=kg, facility_kg=kg, route="[]")
        db.add(p)
        db.flush()
        db.add(PickupLine(pickup_id=p.id, org_id=org_id, ref_type="lot",
                          ref_id=0, kg=kg, tier=tier))
        db.flush()
        if collector:
            D.claim(db, p, db.get(User, collector))
        B.charge_pickup(db, p)
        db.commit()
        inv = db.scalar(select(Invoice).where(Invoice.pickup_id == p.id))
        return p.id, inv.id
    finally:
        db.close()


# ---------- prices are nominal ----------
def test_default_prices():
    db = SessionLocal()
    try:
        ride = db.scalar(select(Plan).where(Plan.code == "ride"))
        assert ride.base_paise == 5000                       # Rs 50 a pickup
        assert set(json.loads(ride.rates).values()) == {500}  # Rs 5 a kg
        assert db.scalar(select(Plan).where(
            Plan.code == "starter")).base_paise == 49900
    finally:
        db.close()


def test_old_default_prices_are_upgraded_but_edited_ones_are_kept():
    db = SessionLocal()
    try:
        ride = db.scalar(select(Plan).where(Plan.code == "ride"))
        keep = (ride.base_paise, ride.rates)
        for base, quota, rates in B.OLD_DEFAULTS["ride"]:   # every old set
            ride.base_paise, ride.rates = base, json.dumps(
                {**rates, "A": 100})              # an old row, with tier A
            db.commit()
            B.ensure_plans(db)
            assert ride.base_paise == 5000
            assert set(json.loads(ride.rates).values()) == {500}
        ride.base_paise = 4321                    # the admin's own price
        db.commit()
        B.ensure_plans(db)
        assert ride.base_paise == 4321
        ride.base_paise, ride.rates = keep
        db.commit()
    finally:
        db.close()


# ---------- the QR itself ----------
def test_upi_uri_carries_the_amount_and_payee(monkeypatch):
    monkeypatch.setattr(C, "UPI_VPA", "shop@okhdfc")
    monkeypatch.setattr(C, "UPI_NAME", "FoodLoop")
    up = P.upi_payload(5250, "FL12", "FoodLoop pickup 7")
    q = parse_qs(urlparse(up["uri"]).query)
    assert up["uri"].startswith("upi://pay?")
    assert q["pa"] == ["shop@okhdfc"] and q["am"] == ["52.50"]
    assert q["cu"] == ["INR"] and q["tr"] == ["FL12"]
    assert up["qr"].startswith("data:image/svg+xml") and not up["demo"]


def test_demo_qr_is_dev_only_and_never_a_real_account(monkeypatch):
    monkeypatch.setattr(C, "UPI_VPA", "")
    up = P.upi_payload(100, "FL1", "x")
    assert up["demo"] and up["vpa"] == P.DEMO_VPA
    monkeypatch.setattr(C, "IS_PROD", True)
    assert P.upi_payload(100, "FL1", "x") is None     # not offered in prod


# ---------- merchant pays by QR ----------
def test_merchant_pays_by_qr_and_admin_checks_it(anon, monkeypatch):
    monkeypatch.setattr(C, "FREE_PICKUPS", 0)
    org = _signup(anon, "9666666601", "Upi")
    anon.put("/api/billing/method", json={"method": "upi"})
    _, iid = _closed_run(org, kg=40)
    r = anon.get(f"/api/billing/invoices/{iid}/upi").json()
    assert r["amount_paise"] == 5000 + 40 * 500 and r["amount"] == 250.0
    assert f"am={r['amount']:.2f}" in r["upi"]["uri"]
    assert r["upi"]["qr"].startswith("data:image/svg+xml")

    bad = anon.post(f"/api/billing/invoices/{iid}/upi-paid",
                    json={"ref": "no spaces!"})
    assert bad.status_code == 422
    ok = anon.post(f"/api/billing/invoices/{iid}/upi-paid",
                   json={"ref": "412345678901"})
    assert ok.status_code == 200
    s = anon.get("/api/billing/status").json()
    assert s["dues"] == []                       # paid, so not blocked
    assert anon.get(f"/api/billing/invoices/{iid}/upi").status_code == 409

    login(anon, "admin@foodloop.local")
    pend = anon.get("/api/billing/admin/summary").json()["upi_pending"]
    mine = [x for x in pend if x["invoice_id"] == iid][0]
    assert mine["ref"] == "412345678901" and mine["amount"] == 250.0
    # the money isn't in the bank: the bill is due again
    assert anon.post(f"/api/billing/admin/upi/{iid}/reject"
                     ).status_code == 200
    login(anon, "9666666601", PW)
    assert [d["id"] for d in anon.get(
        "/api/billing/status").json()["dues"]] == [iid]
    anon.post(f"/api/billing/invoices/{iid}/upi-paid", json={})
    # a second claim on the same bill is refused cleanly
    again = anon.post(f"/api/billing/invoices/{iid}/upi-paid", json={})
    assert again.status_code in (409, 500) and again.status_code == 409
    login(anon, "admin@foodloop.local")
    assert anon.post(f"/api/billing/admin/upi/{iid}/verify"
                     ).status_code == 200
    pend = anon.get("/api/billing/admin/summary").json()["upi_pending"]
    assert all(x["invoice_id"] != iid for x in pend)


def test_only_the_owner_can_use_a_bills_qr(anon, monkeypatch):
    monkeypatch.setattr(C, "FREE_PICKUPS", 0)
    org = _signup(anon, "9666666602", "Owner")
    _, iid = _closed_run(org)
    _signup(anon, "9666666603", "Snoop")
    assert anon.get(f"/api/billing/invoices/{iid}/upi").status_code == 404
    assert anon.post(f"/api/billing/invoices/{iid}/upi-paid",
                     json={}).status_code == 404


# ---------- the collector sees the amount and the QR too ----------
def test_collector_sees_each_merchants_amount_and_qr(anon, monkeypatch):
    monkeypatch.setattr(C, "FREE_PICKUPS", 0)
    db = SessionLocal()
    try:
        u = User(name="Bill Driver", phone="9666666610", role="hub",
                 status="active", pw_hash=hash_pw(PW))
        db.add(u)
        db.flush()
        db.add(CollectorProfile(user_id=u.id, vehicle="van", capacity_kg=500,
                                base_lat=28.5, base_lng=77.4, available=False))
        db.commit()
        cid = u.id
    finally:
        db.close()
    org = _signup(anon, "9666666604", "Billed")
    pid, iid = _closed_run(org, kg=20, collector=cid)

    login(anon, "9666666610", PW)
    rows = anon.get(f"/api/hub/runs/{pid}/bills").json()
    assert len(rows) == 1 and rows[0]["org"] == "Billed Foods"
    assert rows[0]["amount_paise"] == 5000 + 20 * 500
    assert rows[0]["status"] == "due"
    assert rows[0]["upi"]["qr"].startswith("data:image/svg+xml")
    assert "am=150.00" in rows[0]["upi"]["uri"]
    assert [x["label"] for x in rows[0]["lines"]][0] == "Pickup fee"

    # another collector may not read this run's bills
    other = _signup(anon, "9666666605", "NotACollector")
    assert other and anon.get(
        f"/api/hub/runs/{pid}/bills").status_code == 403
    # paid bills carry no QR
    login(anon, "9666666604", PW)
    anon.put("/api/billing/method", json={"method": "upi"})
    anon.post(f"/api/billing/invoices/{iid}/upi-paid", json={})
    login(anon, "9666666610", PW)
    row = anon.get(f"/api/hub/runs/{pid}/bills").json()[0]
    assert row["status"] == "paid" and row["upi"] is None
