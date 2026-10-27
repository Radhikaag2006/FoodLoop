import json

import pytest
from sqlalchemy import select

from app import config as C
from app import billing as B
from app import payments as P
from app.db import SessionLocal
from app.models import Invoice, Pickup, PickupLine, Plan, User
from conftest import login


# ---------- gateway safety ----------
def _keys(monkeypatch, kid, secret="secret", live_ok=False):
    monkeypatch.setattr(C, "RAZORPAY_KEY_ID", kid)
    monkeypatch.setattr(C, "RAZORPAY_KEY_SECRET", secret)
    monkeypatch.setattr(C, "ALLOW_LIVE_PAYMENTS", live_ok)


def test_no_keys_uses_simulator(monkeypatch):
    _keys(monkeypatch, "", "")
    assert P.mode() == "mock"
    monkeypatch.setattr(C, "IS_PROD", True)
    assert P.mode() == "off"            # never simulate in production


def test_live_keys_are_refused(monkeypatch):
    _keys(monkeypatch, "rzp_live_abc")
    assert P.mode() == "off"
    _keys(monkeypatch, "rzp_live_abc", live_ok=True)
    assert P.mode() == "razorpay"
    _keys(monkeypatch, "rzp_test_abc")
    assert P.mode() == "razorpay"
    _keys(monkeypatch, "garbage")
    assert P.mode() == "off"


def test_signature_check(monkeypatch):
    _keys(monkeypatch, "rzp_test_abc", "s3cret")
    sig = P.signature("order_1", "pay_1", "s3cret")
    assert P.verify("order_1", "pay_1", sig)
    assert not P.verify("order_1", "pay_2", sig)
    assert not P.verify("order_1", "pay_1", "0" * 64)
    assert not P.verify("order_1", "pay_1", "")


# ---------- price maths ----------
RATES = {"B": 200, "C": 200, "D": 400, "E": 300}


def test_ride_amount():
    assert B._amount({"B": 10, "D": 5}, RATES, 5000) == 5000 + 2000 + 2000
    assert B._amount({}, RATES, 0) == 0
    assert B._amount({"B": 0.1}, RATES, 0) == B.MIN_PAISE   # Rs 1 floor


# ---------- flows through the API ----------
def _org_of(phone):
    db = SessionLocal()
    try:
        return db.scalar(select(User).where(User.phone == phone)).org_id
    finally:
        db.close()


def _signup(c, phone, name):
    """A fresh business (demo accounts get their passwords changed by
    other tests). Signing up also signs in."""
    c.cookies.clear()
    r = c.post("/api/auth/signup", json={
        "role": "business", "name": name, "phone": phone,
        "password": "Strong123", "org_name": name + " Foods",
        "address": "Sector 1", "city": "Noida"})
    assert r.status_code == 200, r.text
    return _org_of(phone)


def _closed_pickup(org_id, kg=40.0, tier="D"):
    db = SessionLocal()
    try:
        p = Pickup(facility_id=1, status="closed", expected_kg=kg,
                   hub_kg=kg, facility_kg=kg)
        db.add(p)
        db.flush()
        db.add(PickupLine(pickup_id=p.id, org_id=org_id, ref_type="lot",
                          ref_id=0, kg=kg, tier=tier))
        db.flush()
        B.charge_pickup(db, p)
        db.commit()
        return p.id
    finally:
        db.close()


LOT = {"item": "vegetables", "condition": "spoiled", "qty_kg": 5}


def test_new_business_gets_free_trial(anon):
    _signup(anon, "9333333300", "Trial")
    s = anon.get("/api/billing/status").json()
    assert s["trial"] == {"total": 3, "pickups": 0, "left": 3}
    assert s["can_add"] and s["plan"] is None
    for _ in range(3):                       # three pickups, all free
        _closed_pickup(_org_of("9333333300"), kg=10)
    s = anon.get("/api/billing/status").json()
    assert s["trial"]["left"] == 0 and s["dues"] == []
    assert not s["can_add"]
    _closed_pickup(_org_of("9333333300"), kg=10)       # the fourth costs
    assert len(anon.get("/api/billing/status").json()["dues"]) == 1


def test_trial_then_plan_gate(anon, monkeypatch):
    monkeypatch.setattr(C, "FREE_PICKUPS", 0)
    _signup(anon, "9333333301", "Gate")
    s = anon.get("/api/billing/status").json()
    assert not s["can_add"] and s["trial"]["left"] == 0
    r = anon.post("/api/business/lots", json=LOT)
    assert r.status_code == 402
    # pay per ride needs a payment method on file first
    assert anon.post("/api/billing/plans/ride/select").status_code == 409
    assert anon.put("/api/billing/method",
                    json={"method": "upi"}).status_code == 200
    assert anon.post("/api/billing/plans/ride/select").status_code == 200
    assert anon.get("/api/billing/status").json()["can_add"]
    assert anon.post("/api/business/lots", json=LOT).status_code == 200


def test_ride_invoice_blocks_until_paid(anon, monkeypatch):
    monkeypatch.setattr(C, "FREE_PICKUPS", 0)
    org = _signup(anon, "9333333302", "Ride")
    pid = _closed_pickup(org, kg=40, tier="D")
    due = anon.get("/api/billing/status").json()["dues"]
    mine = [d for d in due if d["pickup_id"] == pid][0]
    assert mine["amount_paise"] == 5000 + 40 * 500
    assert anon.post("/api/business/lots", json=LOT).status_code == 402

    # someone else's invoice is invisible
    _signup(anon, "9333333303", "Other")
    assert anon.post(
        f"/api/billing/invoices/{mine['id']}/order").status_code == 404

    login(anon, "9333333302", "Strong123")
    o = anon.post(f"/api/billing/invoices/{mine['id']}/order")
    assert o.status_code == 200 and o.json()["amount_paise"] == 25000
    assert o.json()["mode"] == "mock"
    assert anon.post(
        f"/api/billing/invoices/{mine['id']}/simulate-pay").status_code == 200
    # paid, but the trial is over, so a plan is still needed
    assert anon.post("/api/business/lots", json=LOT).status_code == 402
    anon.put("/api/billing/method", json={"method": "card"})
    anon.post("/api/billing/plans/ride/select")
    assert anon.post("/api/business/lots", json=LOT).status_code == 200


def test_monthly_plan_quota(anon, monkeypatch):
    monkeypatch.setattr(C, "FREE_PICKUPS", 0)
    org = _signup(anon, "9333333304", "Monthly")
    r = anon.post("/api/billing/plans/starter/select").json()["invoice"]
    assert r["amount_paise"] == 49900
    # not subscribed until paid
    assert not anon.get("/api/billing/status").json()["can_add"]
    anon.post(f"/api/billing/invoices/{r['id']}/order")
    anon.post(f"/api/billing/invoices/{r['id']}/simulate-pay")
    s = anon.get("/api/billing/status").json()
    assert s["plan"]["code"] == "starter" and s["can_add"]

    _closed_pickup(org, kg=60)                  # inside the 100 kg quota
    db = SessionLocal()
    inv = db.scalars(select(Invoice).where(
        Invoice.org_id == org, Invoice.kind == "ride")
        .order_by(Invoice.id.desc())).first()
    assert inv.amount_paise == 0 and inv.status == "paid"
    db.close()

    _closed_pickup(org, kg=60)                  # 20 kg over: 20 * Rs 5
    db = SessionLocal()
    inv = db.scalars(select(Invoice).where(
        Invoice.org_id == org, Invoice.kind == "ride")
        .order_by(Invoice.id.desc())).first()
    assert inv.amount_paise == 20 * 500 and inv.status == "due"
    db.close()

    # cannot jump to ride plan mid-month
    anon.put("/api/billing/method", json={"method": "upi"})
    r = anon.post("/api/billing/plans/ride/select")
    assert r.status_code == 409 and "monthly plan" in r.json()["detail"]


def test_verify_rejects_bad_signature(anon, monkeypatch):
    _keys(monkeypatch, "rzp_test_abc", "s3cret")
    monkeypatch.setattr(P, "create_order", lambda *a, **k: "order_X1")
    monkeypatch.setattr(C, "FREE_PICKUPS", 0)
    org = _signup(anon, "9333333305", "Verify")
    pid = _closed_pickup(org, kg=10, tier="D")
    inv = [d for d in anon.get("/api/billing/status").json()["dues"]
           if d["pickup_id"] == pid][0]
    assert anon.post(f"/api/billing/invoices/{inv['id']}/order"
                     ).json()["key_id"] == "rzp_test_abc"
    # simulator is off while Razorpay is configured
    assert anon.post(
        f"/api/billing/invoices/{inv['id']}/simulate-pay").status_code == 404
    url = f"/api/billing/invoices/{inv['id']}/verify"
    bad = {"razorpay_order_id": "order_X1", "razorpay_payment_id": "pay_1",
           "razorpay_signature": "0" * 64}
    assert anon.post(url, json=bad).status_code == 400
    wrong_order = {**bad, "razorpay_order_id": "order_OTHER",
                   "razorpay_signature": P.signature(
                       "order_OTHER", "pay_1", "s3cret")}
    assert anon.post(url, json=wrong_order).status_code == 400
    good = {**bad, "razorpay_signature": P.signature(
        "order_X1", "pay_1", "s3cret")}
    assert anon.post(url, json=good).status_code == 200
    db = SessionLocal()
    assert db.get(Invoice, inv["id"]).status == "paid"
    db.close()


def test_admin_can_edit_prices(anon):
    login(anon, "admin@foodloop.local")
    s = anon.get("/api/billing/admin/summary").json()
    ride = [p for p in s["plans"] if p["code"] == "ride"][0]
    body = {"name": ride["name"], "base_paise": 6000, "quota_kg": 0,
            "rates": {t: int(v * 100) for t, v in ride["rates"].items()},
            "active": True}
    assert anon.put("/api/billing/admin/plans/ride", json=body
                    ).status_code == 200
    body["base_paise"] = ride["base_paise"]
    assert anon.put("/api/billing/admin/plans/ride", json=body
                    ).status_code == 200
    login(anon, "9000000005")                  # businesses cannot
    assert anon.get("/api/billing/admin/summary").status_code == 403


# ---------- payment method and the itemised bill ----------
def test_payment_method_is_validated_and_saved(anon):
    _signup(anon, "9333333310", "Method")
    assert anon.get("/api/billing/status").json()["pay_pref"] is None
    assert anon.put("/api/billing/method",
                    json={"method": "bitcoin"}).status_code == 422
    assert anon.put("/api/billing/method", json={
        "method": "upi", "vpa": "not a upi id"}).status_code == 422
    ok = anon.put("/api/billing/method", json={
        "method": "upi", "vpa": "shop.owner@okaxis"})
    assert ok.json()["pay_pref"] == {"method": "upi",
                                     "vpa": "shop.owner@okaxis"}
    # a UPI ID is dropped when the method changes to something else
    anon.put("/api/billing/method", json={"method": "card",
                                          "vpa": "shop.owner@okaxis"})
    assert anon.get("/api/billing/status").json()["pay_pref"] == {
        "method": "card", "vpa": ""}


def test_bill_is_itemised_and_the_payment_window_opens_on_their_method(
        anon, monkeypatch):
    monkeypatch.setattr(C, "FREE_PICKUPS", 0)
    org = _signup(anon, "9333333311", "Itemised")
    anon.put("/api/billing/method", json={"method": "upi",
                                          "vpa": "me@okicici"})
    pid = _closed_pickup(org, kg=25, tier="D")
    due = anon.get("/api/billing/status").json()["dues"]
    inv = [d for d in due if d["pickup_id"] == pid][0]
    labels = [x["label"] for x in inv["lines"]]
    assert labels[0] == "Pickup fee" and "Recover" in labels[1]
    assert "25.0 kg" in labels[1]
    assert sum(x["amount_paise"] for x in inv["lines"]) == inv[
        "amount_paise"] == 5000 + 25 * 500
    o = anon.post(f"/api/billing/invoices/{inv['id']}/order").json()
    assert o["method"] == "upi" and o["prefill"]["method"] == "upi"
    assert o["prefill"]["vpa"] == "me@okicici"


def test_minimum_charge_still_adds_up():
    lines = B._fit(B._lines({"B": 0.1}, RATES, 0), B.MIN_PAISE)
    assert sum(x["amount_paise"] for x in lines) == B.MIN_PAISE
