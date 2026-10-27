import json
from datetime import timedelta

from sqlalchemy import select

from app import dispatch as D
from app import tracking as T
from app.clock import utcnow
from app.db import SessionLocal
from app.models import Facility, Lot, Pickup, PickupLine, User
from conftest import login

HUB = "9000000007"
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


def _add_lot(c, kg=20):
    r = c.post("/api/business/lots", json={
        "item": "vegetables", "condition": "overripe", "qty_kg": kg})
    assert r.status_code == 200, r.text
    return r.json()["lot"]


def test_code_formats():
    assert T.norm("fl-7k2p9qxm") == "FL-7K2P9QXM"
    assert T.norm(" FL 7K2P 9QXM ") == "FL-7K2P9QXM"
    assert T.norm("7k2p9qxm") == "FL-7K2P9QXM"
    assert T.norm("FL-123") == "" and T.norm("") == ""


def test_every_lot_gets_a_unique_id_and_qr(anon):
    _signup(anon, "9777777701", "Track")
    a, b = _add_lot(anon), _add_lot(anon)
    assert a["track_code"].startswith("FL-") and len(a["track_code"]) == 11
    assert a["track_code"] != b["track_code"]
    lots = {x["id"]: x["track_code"] for x in
            anon.get("/api/business/lots").json()}
    assert lots[a["id"]] == a["track_code"]            # stays the same
    d = anon.get(f"/api/business/lots/{a['id']}").json()
    assert d["track"]["code"] == a["track_code"]
    assert d["track"]["url"].endswith("/track/" + a["track_code"])
    assert d["track"]["qr"].startswith("data:image/svg+xml")
    mine = anon.get(f"/api/track/lot/{a['id']}").json()
    assert mine["code"] == a["track_code"]
    # someone else's lot is off limits
    _signup(anon, "9777777702", "Other")
    assert anon.get(f"/api/track/lot/{a['id']}").status_code == 404


def test_lots_from_before_tracking_get_an_id_on_first_look(anon):
    org = _signup(anon, "9777777703", "Old")
    db = SessionLocal()
    try:
        lot = Lot(org_id=org, item="vegetables", condition="spoiled",
                  qty_kg=5, tier="D")
        db.add(lot)
        db.commit()
        lid = lot.id
    finally:
        db.close()
    row = [x for x in anon.get("/api/business/lots").json()
           if x["id"] == lid][0]
    assert row["track_code"].startswith("FL-")


def test_the_whole_journey_is_visible_from_the_id(anon):
    org = _signup(anon, "9777777704", "Journey")
    lot = _add_lot(anon, kg=20)
    code = lot["track_code"]

    db = SessionLocal()
    try:
        fac = db.scalar(select(Facility).where(Facility.kind == "biogas"))
        p = Pickup(facility_id=fac.id, status="planned", expected_kg=20.0,
                   route="[]")
        db.add(p)
        db.flush()
        db.add(PickupLine(pickup_id=p.id, org_id=org, ref_type="lot",
                          ref_id=lot["id"], kg=20, tier="D"))
        db.get(Lot, lot["id"]).pickup_id = p.id
        collector = db.scalar(select(User).where(User.phone == HUB))
        D.claim(db, p, collector)
        T.event(db, p.id, "planned")
        db.commit()
        pid, plant = p.id, fac.name
    finally:
        db.close()

    anon.cookies.clear()                       # no sign-in needed to track

    def now():
        return anon.get("/api/track/" + code.lower()).json()

    t = now()
    assert t["state"] == "planned" and t["plant"]["name"] == plant
    assert [s["done"] for s in t["steps"]] == [True, True] + [False] * 4
    assert t["steps"][2].get("current") and t["how_used"] is None

    login(anon, HUB)
    at = (utcnow() + timedelta(hours=3)).isoformat() + "+00:00"
    assert anon.post(f"/api/hub/runs/{pid}/schedule",
                     json={"at": at}).status_code == 200
    anon.cookies.clear()
    assert now()["state"] == "scheduled"
    assert "arriving" in now()["steps"][1]["detail"].lower()

    login(anon, HUB)
    assert anon.post(f"/api/hub/runs/{pid}/collect").status_code == 200
    anon.cookies.clear()
    t = now()
    assert t["state"] == "in_transit" and t["state_label"].startswith("On the way")
    assert t["steps"][2]["done"] and t["steps"][2]["at"]
    assert t["steps"][3].get("current")

    login(anon, HUB)
    r = anon.post(f"/api/hub/runs/{pid}/close",
                  json={"hub_kg": 20, "facility_kg": 20})
    assert r.status_code == 200, r.text
    anon.cookies.clear()
    t = now()
    assert t["state"] == "delivered" and all(s["done"] for s in t["steps"])
    assert "biogas" in t["how_used"].lower()
    assert t["record"].startswith("FL-") and t["confirmed_kg"] == 20
    assert t["weights_match"] is True and t["co2e_kg"] > 0
    assert t["steps"][4]["at"]                      # real arrival time

    # privacy: the public page never names people or gives phone numbers
    text = json.dumps(t).lower()
    for leak in ("journey foods", "9777777704", "imran", HUB, "phone"):
        assert leak not in text


def test_unknown_ids_are_not_found_and_guessing_is_slowed(anon):
    assert anon.get("/api/track/FL-AAAAAAAA").status_code == 404
    assert anon.get("/api/track/not-an-id").status_code == 404
    codes = [anon.get("/api/track/FL-AAAAAAAA").status_code
             for _ in range(50)]
    assert 429 in codes                              # throttled
    anon.cookies.clear()
    from app import security
    security._hits.clear()
