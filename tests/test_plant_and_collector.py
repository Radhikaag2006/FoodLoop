from datetime import timedelta

from sqlalchemy import select

from app.clock import utcnow
from app.db import SessionLocal
from app.models import Facility, Pickup, PickupLine, User
from conftest import login

PDF = b"%PDF-1.4\n%fake but valid header\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
HUB, ADMIN = "9000000007", "admin@foodloop.local"


def _signup(c, phone, name):
    c.cookies.clear()
    r = c.post("/api/auth/signup", json={
        "role": "business", "name": name, "phone": phone,
        "password": "Strong123", "org_name": name + " Foods",
        "address": "Sector 1", "city": "Noida"})
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        return db.scalar(select(User).where(User.phone == phone)).org_id
    finally:
        db.close()


def _planned_pickup(*org_ids):
    db = SessionLocal()
    try:
        fid = db.scalars(select(Facility.id)).first()
        p = Pickup(facility_id=fid, status="planned", expected_kg=20.0,
                   route="[]")
        db.add(p)
        db.flush()
        for o in org_ids:
            db.add(PickupLine(pickup_id=p.id, org_id=o, ref_type="lot",
                              ref_id=0, kg=10, tier="D"))
        db.commit()
        return p.id, fid
    finally:
        db.close()


def _in(hours):
    return (utcnow() + timedelta(hours=hours)).isoformat() + "+00:00"


def test_certificate_upload_and_view(anon):
    _, fid = _planned_pickup()
    url = f"/api/facilities/{fid}/document"
    login(anon, ADMIN)
    # only real PDF / PNG / JPEG content is accepted
    bad = anon.post(url, files={"file": ("x.pdf", b"<html>hi</html>")})
    assert bad.status_code == 422
    big = anon.post(url, files={"file": ("x.pdf", PDF + b"0" * 6_000_000)})
    assert big.status_code == 413
    ok = anon.post(url, files={"file": ("cert.pdf", PDF)})
    assert ok.status_code == 200
    assert anon.post(url, files={"file": ("c.png", PNG)}).status_code == 200

    anon.cookies.clear()
    r = anon.get(url)                                # public: no sign-in
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    _signup(anon, "9444444401", "Viewer")
    assert anon.post(url, files={"file": ("c.pdf", PDF)}).status_code == 403

    login(anon, ADMIN)
    assert anon.delete(url).status_code == 200
    assert anon.get(url).status_code == 404


def test_collector_schedule_visible_to_the_business_only(anon):
    a = _signup(anon, "9444444402", "Alpha")
    b = _signup(anon, "9444444403", "Bravo")
    pid, _ = _planned_pickup(a, b)

    login(anon, "9444444402", "Strong123")
    d = anon.get(f"/api/business/pickups/{pid}").json()
    assert d["schedule"] is None                     # nobody assigned yet

    login(anon, HUB)
    assert anon.post(f"/api/hub/runs/{pid}/schedule",
                     json={"at": _in(-3)}).status_code == 422   # the past
    assert anon.post(f"/api/hub/runs/{pid}/schedule",
                     json={"at": _in(24 * 20)}).status_code == 422
    assert anon.post(f"/api/hub/runs/{pid}/schedule",
                     json={"at": "soon"}).status_code == 422
    r = anon.post(f"/api/hub/runs/{pid}/schedule", json={"at": _in(5)})
    assert r.status_code == 200

    login(anon, "9444444402", "Strong123")
    d = anon.get(f"/api/business/pickups/{pid}").json()
    s = d["schedule"]
    assert s["collector"]["name"] == "Imran Khan"
    assert s["collector"]["phone"] == HUB and s["starts"] and s["ends"]
    # the business is told, with the collector's name and number
    notes = anon.get("/api/auth/notifications").json()
    assert any("Pickup time set" in n["title"] and HUB in n["body"]
               for n in notes)
    # other businesses' details are not exposed through the list
    for p in anon.get("/api/business/pickups").json():
        assert "route" not in p


def test_collecting_without_a_booking_assigns_the_collector(anon):
    a = _signup(anon, "9444444404", "Charlie")
    pid, _ = _planned_pickup(a)
    login(anon, HUB)
    assert anon.post(f"/api/hub/runs/{pid}/collect").status_code == 200
    login(anon, "9444444404", "Strong123")
    s = anon.get(f"/api/business/pickups/{pid}").json()["schedule"]
    assert s["collector"]["phone"] == HUB


def test_business_sees_plant_card_without_price(anon):
    a = _signup(anon, "9444444405", "Delta")
    pid, fid = _planned_pickup(a)
    d = anon.get(f"/api/business/pickups/{pid}").json()
    card = d["facility_card"]
    assert card["id"] == fid and "lat" in card and "cert_no" in card
    assert not {"rate_per_kg", "est_value", "score"} & set(card)
