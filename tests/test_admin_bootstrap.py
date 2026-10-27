import pytest
from sqlalchemy import select

from app import config as C
from app import seed
from app.db import SessionLocal
from app.models import User
from conftest import login

OLD = ("admin@foodloop.local", "Demo@1234")


def _try(client, ident, pw):
    client.cookies.clear()
    return client.post("/api/auth/login",
                       json={"identifier": ident, "password": pw}).status_code


@pytest.fixture()
def restore_admin(anon, monkeypatch):
    """Other tests sign in as the demo admin, so put it back afterwards."""
    yield
    monkeypatch.setattr(C, "ADMIN_EMAIL", OLD[0])
    monkeypatch.setattr(C, "ADMIN_PASSWORD", OLD[1])
    monkeypatch.setattr(C, "ADMIN_PASSWORD_RESET", True)
    seed.bootstrap()


def test_env_admin_is_ignored_when_an_admin_exists(anon, monkeypatch,
                                                   restore_admin):
    monkeypatch.setattr(C, "ADMIN_EMAIL", "boss@example.com")
    monkeypatch.setattr(C, "ADMIN_PASSWORD", "Boss-Pass-123")
    monkeypatch.setattr(C, "ADMIN_PASSWORD_RESET", False)
    seed.bootstrap()                              # the old behaviour
    assert _try(anon, "boss@example.com", "Boss-Pass-123") == 401
    assert _try(anon, *OLD) == 200


def test_reset_flag_makes_the_env_login_work(anon, monkeypatch,
                                             restore_admin):
    monkeypatch.setattr(C, "ADMIN_EMAIL", "Boss@Example.com")
    monkeypatch.setattr(C, "ADMIN_PASSWORD", "Boss-Pass-123")
    monkeypatch.setattr(C, "ADMIN_PASSWORD_RESET", True)
    seed.bootstrap()
    assert _try(anon, "boss@example.com", "Boss-Pass-123") == 200
    assert _try(anon, *OLD) == 401                # the old password is gone
    db = SessionLocal()
    try:
        admins = db.scalars(select(User).where(User.role == "admin")).all()
        assert len(admins) == 1 and admins[0].status == "active"
    finally:
        db.close()


def test_reset_does_not_take_another_accounts_email(anon, monkeypatch,
                                                    restore_admin):
    login(anon, "9000000005")                     # a demo business exists
    db = SessionLocal()
    try:
        other = db.scalar(select(User).where(User.phone == "9000000005"))
        other.email = "taken@example.com"
        db.commit()
    finally:
        db.close()
    monkeypatch.setattr(C, "ADMIN_EMAIL", "taken@example.com")
    monkeypatch.setattr(C, "ADMIN_PASSWORD", "Whatever-123")
    monkeypatch.setattr(C, "ADMIN_PASSWORD_RESET", True)
    seed.bootstrap()                              # skipped, not a crash
    assert _try(anon, *OLD) == 200


def test_mismatch_is_explained_in_the_log(anon, monkeypatch, caplog,
                                          restore_admin):
    monkeypatch.setattr(C, "ADMIN_EMAIL", "nobody@example.com")
    monkeypatch.setattr(C, "ADMIN_PASSWORD", "x-Pass-12345")
    monkeypatch.setattr(C, "ADMIN_PASSWORD_RESET", False)
    with caplog.at_level("INFO"):
        seed.bootstrap()
    assert "does not match" in caplog.text and "ADMIN_PASSWORD_RESET" in caplog.text
