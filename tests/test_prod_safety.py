import pytest
from sqlalchemy import select

from app import config as C
from app import seed
from app.db import SessionLocal
from app.models import User
from app.security import hash_pw

OLD = ("admin@foodloop.local", "Demo@1234")


# ---------- what counts as production, and what demo mode may do ----------
def test_production_is_detected_even_without_env():
    assert C.is_production("production")
    assert C.is_production("development", "true")        # Render sets RENDER=true
    assert C.is_production("development", "TRUE")
    assert not C.is_production("development", "")
    assert not C.is_production("development", "false")


def test_demo_mode_never_runs_in_production():
    assert C.demo_allowed(False, True) is True            # laptop: allowed
    assert C.demo_allowed(True, True) is False            # production: ignored
    assert C.demo_allowed(False, False) is False


# ---------- the sign-in screen only offers logins that exist ----------
def test_signin_screen_hides_demo_in_production(anon, monkeypatch):
    monkeypatch.setattr(C, "DEMO_MODE", False)           # what production does
    cat = anon.get("/api/catalog").json()
    assert cat["demo"] is False and cat["demo_admin"] is False


def test_demo_admin_is_offered_only_when_it_exists(anon, monkeypatch):
    monkeypatch.setattr(C, "DEMO_MODE", True)
    monkeypatch.setattr(C, "ADMIN_EMAIL", "")
    monkeypatch.setattr(C, "ADMIN_PASSWORD", "")
    assert anon.get("/api/catalog").json()["demo_admin"] is True
    monkeypatch.setattr(C, "ADMIN_EMAIL", "boss@example.com")   # a real admin
    monkeypatch.setattr(C, "ADMIN_PASSWORD", "Boss-Pass-123")
    cat = anon.get("/api/catalog").json()
    assert cat["demo"] is True and cat["demo_admin"] is False


# ---------- demo accounts on a production database ----------
@pytest.fixture()
def users_untouched():
    """Put every user's status and session version back afterwards, because
    other tests sign in as the demo accounts."""
    db = SessionLocal()
    snap = {u.id: (u.status, u.sv) for u in db.scalars(select(User))}
    db.close()
    yield
    db = SessionLocal()
    for u in db.scalars(select(User)):
        if u.id in snap:
            u.status, u.sv = snap[u.id]
        else:
            db.delete(u)
    db.commit()
    db.close()


def _user(db, phone, pw):
    u = User(name="t", phone=phone, role="business", status="active",
             pw_hash=hash_pw(pw))
    db.add(u)
    db.flush()
    return u


def test_demo_accounts_with_the_public_password_are_switched_off(
        anon, users_untouched):
    db = SessionLocal()
    try:
        demo = _user(db, "9000000991", "Demo@1234")      # still public: off
        changed = _user(db, "9000000992", "Mine-Is-Private-1")   # kept
        real = _user(db, "9876500991", "Demo@1234")      # not a demo number
        db.commit()
        n = seed.disable_demo_accounts(db)
        db.refresh(demo), db.refresh(changed), db.refresh(real)
        assert n >= 1
        assert demo.status == "disabled"
        assert changed.status == "active"
        assert real.status == "active"
    finally:
        db.close()
    r = anon.post("/api/auth/login", json={
        "identifier": "9000000991", "password": "Demo@1234"})
    assert r.status_code == 403                            # "turned off"


# ---------- the admin may not use the published password in production ----
@pytest.fixture()
def restore_admin(anon, monkeypatch):
    yield
    monkeypatch.setattr(C, "IS_PROD", False)
    monkeypatch.setattr(C, "ADMIN_EMAIL", OLD[0])
    monkeypatch.setattr(C, "ADMIN_PASSWORD", OLD[1])
    monkeypatch.setattr(C, "ADMIN_PASSWORD_RESET", True)
    seed.bootstrap()


def test_production_refuses_the_demo_password_for_admin(
        anon, monkeypatch, caplog, restore_admin):
    monkeypatch.setattr(C, "IS_PROD", True)
    monkeypatch.setattr(C, "ADMIN_EMAIL", "boss@example.com")
    monkeypatch.setattr(C, "ADMIN_PASSWORD", "Demo@1234")
    monkeypatch.setattr(C, "ADMIN_PASSWORD_RESET", True)
    with caplog.at_level("ERROR"):
        seed.bootstrap()
    assert "public demo password" in caplog.text
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.role == "admin"))
        assert admin.email == OLD[0]                       # unchanged
    finally:
        db.close()


def test_a_strong_admin_password_is_still_accepted_in_production(
        anon, monkeypatch, restore_admin):
    monkeypatch.setattr(C, "IS_PROD", True)
    monkeypatch.setattr(C, "ADMIN_EMAIL", "boss@example.com")
    monkeypatch.setattr(C, "ADMIN_PASSWORD", "A-Long-Private-Pass-9")
    monkeypatch.setattr(C, "ADMIN_PASSWORD_RESET", True)
    seed.bootstrap()
    anon.cookies.clear()
    r = anon.post("/api/auth/login", json={
        "identifier": "boss@example.com",
        "password": "A-Long-Private-Pass-9"})
    assert r.status_code == 200


# ---------- nothing about demos is shipped to the browser in production ----
def test_website_files_do_not_contain_the_demo_password():
    import glob
    files = glob.glob("static/js/*.js") + glob.glob("templates/*.html")
    leaks = [f for f in files if "Demo@1234" in open(f, encoding="utf-8").read()]
    assert leaks == []


def test_demo_logins_are_sent_only_when_demo_mode_is_on(anon, monkeypatch):
    monkeypatch.setattr(C, "DEMO_MODE", False)           # production
    cat = anon.get("/api/catalog").json()
    assert cat["demo_accounts"] == [] and cat["demo_password"] == ""
    assert "Demo@1234" not in anon.get("/api/catalog").text
    monkeypatch.setattr(C, "DEMO_MODE", True)            # a laptop
    monkeypatch.setattr(C, "ADMIN_EMAIL", "")
    monkeypatch.setattr(C, "ADMIN_PASSWORD", "")
    cat = anon.get("/api/catalog").json()
    labels = [a[0] for a in cat["demo_accounts"]]
    assert labels == ["Business", "Collector", "FoodLoop admin"]
    assert cat["demo_password"] == "Demo@1234"
    monkeypatch.setattr(C, "ADMIN_EMAIL", "boss@example.com")
    monkeypatch.setattr(C, "ADMIN_PASSWORD", "Boss-Pass-123")
    labels = [a[0] for a in anon.get("/api/catalog").json()["demo_accounts"]]
    assert "FoodLoop admin" not in labels
