import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

import pytest
from sqlalchemy import select

from app import config as C
from app import dispatch as D
from app.db import SessionLocal
from app.matching import split_by_capacity
from app.models import (CollectorProfile, Facility, Pickup, PickupLine,
                        User)
from app.security import hash_pw
from conftest import login

PW = "Strong123"


# ---------- fare maths ----------
def test_driver_fare_adds_up():
    total, parts = D.driver_fare(km=20, kg=60, n_stops=2)
    assert parts == {"base": C.DRIVER_BASE_PAISE,
                     "distance": 20 * C.DRIVER_PER_KM_PAISE,
                     "stops": C.DRIVER_PER_STOP_PAISE,
                     "weight": 60 * C.DRIVER_PER_KG_PAISE}
    assert total == sum(parts.values())
    one, _ = D.driver_fare(20, 60, 1)            # one stop: no extra-stop fee
    assert total - one == C.DRIVER_PER_STOP_PAISE


def test_trip_includes_the_drive_back_to_base():
    fac = NS(lat=28.0, lng=77.0)
    stops = [{"lat": 28.1, "lng": 77.1}]
    without = D.trip_km(None, stops, fac)
    base = (28.3, 77.3)
    with_base = D.trip_km(base, stops, fac)
    assert with_base > without > 0


# ---------- splitting a big load to vehicle size ----------
def _row(oid, kg, lat, lng):
    org = NS(id=oid, name=f"o{oid}", lat=lat, lng=lng, address="",
             contact_phone="", collection_point="")
    return ("lot", NS(id=oid, tier="D"), kg, org)


def test_split_respects_vehicle_size():
    fac = NS(lat=28.5, lng=77.5)
    rows = [_row(i, 40, 28.5 + i * 0.05, 77.5) for i in range(1, 5)]  # 160 kg
    loads = split_by_capacity(rows, fac, 100)
    assert len(loads) >= 2
    assert all(sum(r[2] for r in ld) <= 100 for ld in loads)
    assert sum(r[2] for ld in loads for r in ld) == 160
    # a vehicle that fits everything keeps one run; none set = no limit
    assert len(split_by_capacity(rows, fac, 500)) == 1
    assert len(split_by_capacity(rows, fac, None)) == 1


def test_a_lot_bigger_than_the_vehicle_gets_its_own_run():
    fac = NS(lat=28.5, lng=77.5)
    rows = [_row(1, 30, 28.51, 77.5), _row(2, 150, 28.52, 77.5)]
    loads = split_by_capacity(rows, fac, 100)
    assert sorted(sum(r[2] for r in ld) for ld in loads) == [30, 150]


# ---------- choosing the collector ----------
def _collector(phone, name, cap, lat, lng, available=True):
    db = SessionLocal()
    try:
        u = User(name=name, phone=phone, role="hub", status="active",
                 pw_hash=hash_pw(PW))
        db.add(u)
        db.flush()
        db.add(CollectorProfile(user_id=u.id, vehicle="van",
                                capacity_kg=cap, base_lat=lat, base_lng=lng,
                                base_label="t", available=available))
        db.commit()
        return u.id
    finally:
        db.close()


def _run(kg=60.0, lat=29.0, lng=78.0):
    db = SessionLocal()
    try:
        fid = db.scalars(select(Facility.id)).first()
        stops = [{"org_id": 0, "name": "x", "lat": lat, "lng": lng,
                  "address": "", "phone": "", "point": "", "kg": kg}]
        p = Pickup(facility_id=fid, status="planned", expected_kg=kg,
                   route=json.dumps(stops))
        db.add(p)
        db.commit()
        return p.id
    finally:
        db.close()


@pytest.fixture()
def quiet_world():
    """Other collectors must not take part in these dispatch tests."""
    db = SessionLocal()
    before = [(c.id, c.available) for c in db.scalars(
        select(CollectorProfile))]
    for c in db.scalars(select(CollectorProfile)):
        c.available = False
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    for c in db.scalars(select(CollectorProfile)):
        c.available = False                    # leave nobody dispatchable
    for cid, was in before:
        pass
    db.commit()
    db.close()


def test_run_goes_to_nearest_collector_with_room(quiet_world):
    small_near = _collector("9555555501", "SmallNear", 30, 29.0, 78.0)
    big_near = _collector("9555555502", "BigNear", 500, 29.01, 78.01)
    big_far = _collector("9555555503", "BigFar", 500, 28.0, 77.0)
    _collector("9555555504", "Off", 500, 29.0, 78.0, available=False)
    pid = _run(kg=60)
    db = SessionLocal()
    try:
        p = db.get(Pickup, pid)
        D.assign_run(db, p)
        db.commit()
        assert D.owner_of(db, pid) == big_near      # the 30 kg van can't
        # hand it back: the next nearest takes it
        D.decline(db, p, db.get(User, big_near))
        db.commit()
        assert D.owner_of(db, pid) == big_far
        D.decline(db, p, db.get(User, big_far))
        db.commit()
        assert D.owner_of(db, pid) is None          # nobody fits: open
        assert D.assignment_of(db, pid).collector_id is None
    finally:
        db.close()
    assert small_near


def test_busy_collectors_are_passed_over(quiet_world):
    near = _collector("9555555511", "Near", 500, 29.0, 78.0)
    nearish = _collector("9555555512", "Nearish", 500, 29.0, 78.05)  # ~5 km
    db = SessionLocal()
    try:
        owners = []
        for _ in range(3):
            pid = _run(kg=20)
            p = db.get(Pickup, pid)
            D.assign_run(db, p)
            db.commit()
            owners.append(D.owner_of(db, pid))
        # the nearest collector does not get every run
        assert set(owners) == {near, nearish}
    finally:
        db.close()


# ---------- through the API ----------
def test_collector_profile_and_run_visibility(anon, quiet_world):
    me = _collector("9555555521", "Me", 500, 29.0, 78.0)
    other = _collector("9555555522", "Other", 500, 28.0, 77.0)
    mine, theirs, open_run = _run(60), _run(60), _run(60)
    db = SessionLocal()
    try:
        D.assign_run(db, db.get(Pickup, mine))        # nearest is "Me"
        theirs_p = db.get(Pickup, theirs)
        a = D.claim(db, theirs_p, db.get(User, other))
        a.collector_id = other
        db.commit()
    finally:
        db.close()

    login(anon, "9555555521", PW)
    prof = anon.get("/api/hub/profile").json()["profile"]
    assert prof["capacity_kg"] == 500
    bad = anon.put("/api/hub/profile", json={
        "capacity_kg": 0, "base_lat": 28, "base_lng": 77})
    assert bad.status_code == 422
    bad = anon.put("/api/hub/profile", json={
        "capacity_kg": 100, "base_lat": 0, "base_lng": 0})
    assert bad.status_code == 422

    rows = {r["id"]: r for r in anon.get("/api/hub/runs").json()}
    assert mine in rows and rows[mine]["mine"]
    assert theirs not in rows                       # someone else's run
    assert open_run in rows and rows[open_run]["open"]
    fare = rows[mine]["fare"]
    assert fare["total_paise"] == sum(
        round(v * 100) for v in fare["parts"].values())
    assert fare["total"] > 0 and fare["km"] > 0

    # I can't hand back or take over someone else's run
    assert anon.post(f"/api/hub/runs/{theirs}/decline").status_code == 403
    assert anon.post(f"/api/hub/runs/{theirs}/collect").status_code == 403
    # handing mine back sends it on to the other collector
    assert anon.post(f"/api/hub/runs/{mine}/decline").status_code == 200
    db = SessionLocal()
    try:
        assert D.owner_of(db, mine) == other
    finally:
        db.close()
    assert me


def test_business_sees_collector_before_a_time_is_set(anon, quiet_world):
    _collector("9555555531", "Driver", 500, 29.0, 78.0)
    anon.cookies.clear()
    r = anon.post("/api/auth/signup", json={
        "role": "business", "name": "Echo", "phone": "9555555532",
        "password": PW, "org_name": "Echo Foods",
        "address": "Sector 1", "city": "Noida"})
    assert r.status_code == 200
    db = SessionLocal()
    try:
        org = db.scalar(select(User).where(User.phone == "9555555532")).org_id
        pid = _run(30)
        db.add(PickupLine(pickup_id=pid, org_id=org, ref_type="lot",
                          ref_id=0, kg=30, tier="D"))
        D.assign_run(db, db.get(Pickup, pid))
        db.commit()
    finally:
        db.close()
    d = anon.get(f"/api/business/pickups/{pid}").json()
    assert d["schedule"]["collector"]["name"] == "Driver"
    assert d["schedule"]["starts"] is None           # time still to come
    assert "fare" not in d and "fare" not in d["schedule"]
    for p in anon.get("/api/business/pickups").json():
        assert "fare" not in p


def test_closing_a_run_freezes_the_fare_for_admin(anon, quiet_world):
    cid = _collector("9555555541", "Closer", 500, 29.0, 78.0)
    anon.cookies.clear()
    anon.post("/api/auth/signup", json={
        "role": "business", "name": "Foxtrot", "phone": "9555555542",
        "password": PW, "org_name": "Foxtrot Foods",
        "address": "Sector 1", "city": "Noida"})
    db = SessionLocal()
    try:
        org = db.scalar(select(User).where(User.phone == "9555555542")).org_id
        pid = _run(40)
        db.add(PickupLine(pickup_id=pid, org_id=org, ref_type="lot",
                          ref_id=0, kg=40, tier="D"))
        D.assign_run(db, db.get(Pickup, pid))
        db.commit()
    finally:
        db.close()

    login(anon, "admin@foodloop.local")
    before = anon.get("/api/billing/admin/summary").json()["driver_cost"]
    login(anon, "9555555541", PW)
    assert anon.post(f"/api/hub/runs/{pid}/collect").status_code == 200
    r = anon.post(f"/api/hub/runs/{pid}/close",
                  json={"hub_kg": 40, "facility_kg": 40})
    assert r.status_code == 200, r.text
    frozen = r.json()["fare"]["total"]
    db = SessionLocal()
    try:
        a = D.assignment_of(db, pid)
        assert a.fare_paise == round(frozen * 100) and a.collector_id == cid
    finally:
        db.close()
    login(anon, "admin@foodloop.local")
    s = anon.get("/api/billing/admin/summary").json()
    assert round(s["driver_cost"] - before, 2) == frozen


# ---------- the collector's week and accepting runs ----------
def test_offer_then_accept_shows_in_the_week(anon, quiet_world):
    me = _collector("9555555551", "Weekly", 500, 29.0, 78.0)
    pid = _run(60)
    db = SessionLocal()
    try:
        D.assign_run(db, db.get(Pickup, pid))
        db.commit()
    finally:
        db.close()
    login(anon, "9555555551", PW)
    w = anon.get("/api/hub/week").json()
    offer = next(r for r in w["offers"] if r["id"] == pid)
    assert offer["fare"]["total"] > 0 and offer["fare"]["km"] > 0
    assert not offer["accepted"]
    assert pid not in [r["id"] for d in w["days"] for r in d["runs"]]

    assert anon.post(f"/api/hub/runs/{pid}/accept").status_code == 200
    w = anon.get("/api/hub/week").json()
    assert pid not in [r["id"] for r in w["offers"]]
    assert pid in [r["id"] for r in w["unscheduled"]]
    assert w["week_total"] >= offer["fare"]["total"]

    soon = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    assert anon.post(f"/api/hub/runs/{pid}/schedule",
                     json={"at": soon}).status_code == 200
    w = anon.get("/api/hub/week").json()
    booked = [r for d in w["days"] for r in d["runs"]]
    assert pid in [r["id"] for r in booked]
    assert sum(d["total"] for d in w["days"]) > 0
    assert me


def test_cant_accept_someone_elses_run(anon, quiet_world):
    _collector("9555555561", "Mine", 500, 29.0, 78.0)
    other = _collector("9555555562", "Theirs", 500, 28.0, 77.0)
    pid = _run(60)
    db = SessionLocal()
    try:
        D.claim(db, db.get(Pickup, pid), db.get(User, other))
        db.commit()
    finally:
        db.close()
    login(anon, "9555555561", PW)
    assert anon.post(f"/api/hub/runs/{pid}/accept").status_code == 403


def test_handing_back_makes_it_an_offer_again(quiet_world):
    a = _collector("9555555571", "A", 500, 29.0, 78.0)
    b = _collector("9555555572", "B", 500, 29.01, 78.01)
    pid = _run(40)
    db = SessionLocal()
    try:
        p = db.get(Pickup, pid)
        D.assign_run(db, p)
        first = D.owner_of(db, pid)
        D.accept(db, p, db.get(User, first))
        assert D.is_accepted(db, p)
        D.decline(db, p, db.get(User, first))
        assert D.owner_of(db, pid) in (a, b) and not D.is_accepted(db, p)
    finally:
        db.close()


# ---------- clubbing small groups ----------
def test_small_group_rides_with_a_nearby_run_else_waits():
    from app.matching import _club_target
    db = SessionLocal()
    try:
        fac = db.scalars(select(Facility)).first()
        tier = sorted(fac.tiers)[0]
        row = lambda lat, lng: ("lot", NS(tier=tier), 3.0, NS(lat=lat, lng=lng))
        near = [row(fac.lat + 0.05, fac.lng)]            # ~5 km away
        far = [row(fac.lat + 5.0, fac.lng)]              # ~550 km away
        assert _club_target(db, near, {fac.id: []}) == fac.id
        assert _club_target(db, far, {fac.id: []}) is None
        assert _club_target(db, near, {}) is None        # no run to join
    finally:
        db.close()
