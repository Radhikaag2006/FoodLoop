import itertools

import pytest
from sqlalchemy import select

from app import config as C
from app import dispatch as D
from app import optimizer as O
from app import travel as TV
from app.db import SessionLocal
from app.matching import haversine
from app.models import Pickup, RunAssignment, TripLog, User
from conftest import login
from test_dispatch import PW, _collector, _run, quiet_world  # noqa: F401


def db_phone(uid):
    db = SessionLocal()
    try:
        return db.get(User, uid).phone
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _app_db(boot):
    """The database tables exist once the app has started."""


# ---------- the solver itself ----------
def test_two_runs_two_drivers_solver_beats_greedy():
    # driver X: A 0.5 km, B 5.5 km; driver Y: A 0.5 km, B 10.5 km
    cost = [[0.5, 5.5], [0.5, 10.5]]
    held = [0, 0]
    g = O.greedy_costs(cost, held, load_km=6)
    s, status = O.solve_costs(cost, held, load_km=6)
    total = lambda a: sum(cost[d][r] for r, d in enumerate(a))
    assert total(g) == 11 and total(s) == 6
    assert status == "optimal"


def _geo_run(i, kg, lat, lng, banned=()):
    return O.Run(i, kg, [(lat, lng)], (28.5, 77.5), set(banned))


def test_capacity_is_a_hard_rule():
    tv = TV.Travel([(28.5, 77.5), (28.6, 77.6), (28.7, 77.7)])
    small = O.Driver(1, (28.5, 77.5), 30)          # nearest, but too small
    big = O.Driver(2, (28.7, 77.7), 500)
    res = O.solve([_geo_run(10, 60, 28.6, 77.6)], [small, big], tv)
    assert res.assign[10] == 2
    # nobody fits: the run is left unassigned, never forced onto a van
    res = O.solve([_geo_run(11, 900, 28.6, 77.6)], [small, big], tv)
    assert res.assign[11] is None


def test_a_driver_who_declined_never_gets_it_back():
    tv = TV.Travel([(28.5, 77.5), (28.6, 77.6), (29.5, 78.5)])
    near, far = O.Driver(1, (28.5, 77.5), 500), O.Driver(2, (29.5, 78.5), 500)
    res = O.solve([_geo_run(1, 50, 28.6, 77.6, banned={1})], [near, far], tv)
    assert res.assign[1] == 2


def test_two_opt_is_never_worse_than_nearest_neighbour():
    plant = (28.5, 77.5)
    pts = [(28.5 + .05 * ((i * 7) % 5), 77.5 + .05 * ((i * 3) % 4))
           for i in range(8)]
    tv = TV.Travel(pts + [plant])
    nn, left, cur = [], set(range(len(pts))), plant
    while left:
        n = min(left, key=lambda i: tv.km(cur, pts[i]))
        nn.append(n), left.remove(n)
        cur = pts[n]
    best = O.order_stops(pts, plant, tv)
    length = lambda o: tv.path_km([plant] + [pts[i] for i in o] + [plant])
    assert sorted(best) == list(range(len(pts)))
    assert length(best) <= length(nn) + 1e-9


# ---------- travel provider ----------
def test_osrm_failure_falls_back_to_straight_lines(monkeypatch):
    monkeypatch.setattr(C, "OSRM_URL", "http://127.0.0.1:9")   # nothing there
    monkeypatch.setattr(C, "OSRM_TIMEOUT_S", 1)
    a, b = (28.5, 77.5), (28.9, 77.9)
    t = TV.Travel([a, b])
    assert t.source == "haversine"
    assert t.km(a, b) == pytest.approx(
        haversine(*a, *b) * C.ROAD_FACTOR)


def test_osrm_answer_is_used_when_it_works(monkeypatch):
    monkeypatch.setattr(C, "OSRM_URL", "http://osrm.test")
    monkeypatch.setattr(TV, "_osrm_table", lambda pts: (
        [[0, 7.0], [7.5, 0]], [[0, 11.0], [12.0, 0]]))
    a, b = (28.5, 77.5), (28.9, 77.9)
    t = TV.Travel([a, b])
    assert t.source == "osrm" and t.km(a, b) == 7.0 and t.minutes(b, a) == 12


# ---------- dispatch modes ----------
_n = itertools.count(9555556000, 2)


def _two_runs_two_drivers():
    n = next(_n)
    near = _collector(str(n), "NearDrv", 500, 29.0, 78.0)
    far = _collector(str(n + 1), "FarDrv", 500, 29.3, 78.3)
    return near, far, _run(40, 29.0, 78.0), _run(40, 29.3, 78.3)


def test_rules_mode_is_the_old_behaviour(quiet_world, monkeypatch):
    monkeypatch.setattr(C, "DISPATCH_MODE", "rules")
    _two_runs_two_drivers()
    db = SessionLocal()
    try:
        runs = [db.get(Pickup, i) for i in
                db.scalars(select(Pickup.id).order_by(Pickup.id.desc())
                           .limit(2))]
        want = {p.id: D.rank_collectors(db, p)[0][2].id for p in runs[:1]}
        D.dispatch_new(db, runs)
        db.commit()
        for p in runs:
            a = D.assignment_of(db, p.id)
            assert not a.pending and a.collector_id
            assert "rules" in a.reason
        assert D.owner_of(db, runs[0].id) == want[runs[0].id]
    finally:
        db.close()


def test_solver_mode_batches_then_assigns(anon, quiet_world, monkeypatch):
    monkeypatch.setattr(C, "DISPATCH_MODE", "solver")
    monkeypatch.setattr(C, "DISPATCH_BATCH_SECONDS", 3600)
    near, far, r1, r2 = _two_runs_two_drivers()
    near_phone = db_phone(near)
    db = SessionLocal()
    try:
        D.dispatch_new(db, [db.get(Pickup, r1), db.get(Pickup, r2)])
        db.commit()
        assert all(D.assignment_of(db, r).pending for r in (r1, r2))
        assert D.assign_batch(db)["runs"] == 0       # window still open
    finally:
        db.close()
    login(anon, near_phone, PW)                     # drivers don't see it
    w = anon.get("/api/hub/week").json()
    assert not {r1, r2} & {x["id"] for x in w["offers"]}
    assert not {r1, r2} & {x["id"] for x in anon.get("/api/hub/runs").json()}

    login(anon, "admin@foodloop.local")
    assert anon.get("/api/admin/dispatch").json()["pending"] >= 2
    out = anon.post("/api/admin/dispatch/run").json()
    assert out["runs"] == 2 and out["status"] in ("optimal", "feasible")
    db = SessionLocal()
    try:
        assert D.owner_of(db, r1) == near and D.owner_of(db, r2) == far
        a = D.assignment_of(db, r1)
        assert not a.pending and a.reason and a.planned_km > 0
    finally:
        db.close()
    login(anon, near_phone, PW)                     # now it is an offer
    assert r1 in [x["id"] for x in anon.get("/api/hub/week").json()["offers"]]
    login(anon, near_phone, PW)
    assert "why" not in anon.get("/api/hub/runs").json()[0]   # admin only


def test_solver_failure_falls_back_to_rules(quiet_world, monkeypatch):
    monkeypatch.setattr(C, "DISPATCH_MODE", "solver")
    monkeypatch.setattr(C, "DISPATCH_BATCH_SECONDS", 0)

    def boom(*a, **k):
        raise RuntimeError("solver exploded")
    monkeypatch.setattr(O, "solve", boom)
    near, far, r1, r2 = _two_runs_two_drivers()
    db = SessionLocal()
    try:
        D.dispatch_new(db, [db.get(Pickup, r1), db.get(Pickup, r2)])
        db.commit()
        for r in (r1, r2):
            a = D.assignment_of(db, r)
            assert not a.pending and a.collector_id
            assert a.reason.startswith("fallback to rules")
    finally:
        db.close()


def test_declined_run_is_replanned_without_that_driver(quiet_world,
                                                       monkeypatch):
    monkeypatch.setattr(C, "DISPATCH_MODE", "solver")
    monkeypatch.setattr(C, "DISPATCH_BATCH_SECONDS", 0)
    near, far, r1, r2 = _two_runs_two_drivers()
    db = SessionLocal()
    try:
        D.dispatch_new(db, [db.get(Pickup, r1), db.get(Pickup, r2)])
        db.commit()
        D.decline(db, db.get(Pickup, r1), db.get(User, near))
        db.commit()
        assert D.owner_of(db, r1) == far            # never back to `near`
        D.decline(db, db.get(Pickup, r1), db.get(User, far))
        db.commit()
        assert D.owner_of(db, r1) is None            # open-claim fallback
    finally:
        db.close()


def test_shadow_mode_keeps_the_rules_and_records_the_solver(quiet_world,
                                                            monkeypatch):
    monkeypatch.setattr(C, "DISPATCH_MODE", "shadow")
    near, far, r1, r2 = _two_runs_two_drivers()
    db = SessionLocal()
    try:
        D.dispatch_new(db, [db.get(Pickup, r1), db.get(Pickup, r2)])
        db.commit()
        for r in (r1, r2):
            a = D.assignment_of(db, r)
            assert "rules" in a.reason and not a.pending
            assert a.collector_id and a.shadow_driver and a.shadow_km > 0
    finally:
        db.close()


def test_trip_log_follows_a_run(quiet_world, monkeypatch):
    monkeypatch.setattr(C, "DISPATCH_MODE", "rules")
    near = _collector("9555555611", "Logger", 500, 29.0, 78.0)
    pid = _run(40, 29.0, 78.0)
    db = SessionLocal()
    try:
        p = db.get(Pickup, pid)
        D.assign_run(db, p)
        D.accept(db, p, db.get(User, near))
        D.log_mark(db, pid, near, "started_at")
        p.hub_kg = 39
        D.settle(db, p)
        db.commit()
        row = db.scalar(select(TripLog).where(TripLog.run_id == pid))
        assert row.driver_id == near and row.planned_km > 0
        assert row.accepted_at and row.started_at and row.closed_at
        assert row.actual_minutes is not None and row.hub_kg == 39
        assert 0 <= row.hour_of_day < 24 and 0 <= row.weekday < 7
    finally:
        db.close()
    assert RunAssignment
