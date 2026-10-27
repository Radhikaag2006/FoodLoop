from conftest import login

BIZ, BIZ2, HUB = "9000000005", "9000000006", "9000000007"
ADMIN = "admin@foodloop.local"


def test_auth_basics(anon):
    assert anon.get("/api/auth/me").json()["user"] is None
    assert anon.get("/api/business/home").status_code == 401
    r = anon.post("/api/auth/login", json={
        "identifier": BIZ, "password": "wrong"})
    assert r.status_code == 401
    u = login(anon, BIZ)
    assert u["role"] == "business"
    assert anon.get("/api/hub/pool").status_code == 403


def test_password_rules_and_duplicates(anon):
    base = {"role": "business", "name": "T", "phone": "9111111111",
            "password": "short", "org_name": "X", "address": "Y",
            "city": "Noida"}
    assert anon.post("/api/auth/signup", json=base).status_code == 422
    base["password"] = "Strong123"
    base["phone"] = BIZ
    assert anon.post("/api/auth/signup", json=base).status_code == 409


def test_retired_roles_and_routes_are_gone(anon):
    for role in ("resident", "society_admin", "guard"):
        r = anon.post("/api/auth/signup", json={
            "role": role, "name": "Nope", "phone": "9666666666",
            "password": "Strong123"})
        assert r.status_code == 422
    assert anon.get("/api/society/residents").status_code == 404
    assert anon.get("/api/resident/home").status_code == 404
    assert anon.get("/api/guard/today").status_code == 404


def test_business_signup_and_add_lot(anon):
    body = {"role": "business", "name": "New Owner", "phone": "9222222222",
            "password": "Strong123", "org_name": "Fresh Foods",
            "address": "Sector 1", "city": "Noida"}
    r = anon.post("/api/auth/signup", json=body)
    assert r.status_code == 200 and r.json()["org"]["kind"] == "business"
    r = anon.post("/api/business/lots", json={
        "item": "bakery", "condition": "spoiled", "qty_kg": 12,
        "expiry": "2030-01-01"})
    assert r.status_code == 200 and r.json()["lot"]["qty_kg"] == 12
    # good, in-date food is not waste, so it is refused
    r = anon.post("/api/business/lots", json={
        "item": "bakery", "condition": "fresh", "qty_kg": 12,
        "expiry": "2030-01-01"})
    assert r.status_code == 422 and "isn't waste" in r.json()["detail"]
    login(anon, ADMIN)
    pend = anon.get("/api/admin/orgs?status=pending").json()
    assert any(o["name"] == "Fresh Foods" for o in pend)


def test_hub_invite_signup(anon):
    login(anon, ADMIN)
    code = anon.post("/api/admin/invites", json={"note": "Night"}
                     ).json()["code"]
    anon.cookies.clear()
    body = {"role": "hub", "name": "New Hub", "phone": "9444444444",
            "password": "Strong123", "invite_code": code}
    assert anon.post("/api/auth/signup", json=body).status_code == 200
    # a code is reusable until it expires: a second driver can join too
    anon.cookies.clear()
    body["phone"] = "9555555555"
    assert anon.post("/api/auth/signup", json=body).status_code == 200
    login(anon, ADMIN)
    row = next(i for i in anon.get("/api/admin/invites").json()
               if i["code"] == code)
    assert row["uses"] == 2
    # revoking stops new sign-ups, but people already in keep their accounts
    assert anon.delete(f"/api/admin/invites/{row['id']}").status_code == 200
    assert all(i["code"] != code for i in anon.get("/api/admin/invites").json())
    anon.cookies.clear()
    body["phone"] = "9666666666"
    assert anon.post("/api/auth/signup", json=body).status_code == 422
    assert anon.get(f"/api/auth/invite/{code}").status_code == 404


def test_business_and_unverified_gate(anon):
    login(anon, BIZ)
    r = anon.post("/api/business/lots", json={
        "item": "dairy", "condition": "fresh", "qty_kg": 20,
        "expiry": "2020-01-01"})
    j = r.json()
    assert j["tier"] == "D" and j["locked"] == ["B", "C"]
    assert "matches" not in j                 # only the single best plant
    m = j["match"]
    assert m["certified"] and m["name"] and m["lat"] and m["distance_km"]
    # a business never sees prices, fees or scores
    assert not {"rate_per_kg", "est_value", "score"} & set(m)
    assert anon.post("/api/business/lots", json={
        "item": "dairy", "qty_kg": 5}).status_code == 422
    # hub should not plan unverified org lots
    login(anon, HUB)
    pool = anon.get("/api/hub/pool").json()
    assert pool["blocked_kg"] > 0


def test_full_pickup_chain_and_report(anon):
    login(anon, HUB)
    anon.post("/api/hub/plan", json={"min_kg": 1})
    runs = anon.get("/api/hub/runs").json()
    assert runs
    r = runs[0]
    assert anon.post(f"/api/hub/runs/{r['id']}/close",
                     json={"hub_kg": 1, "facility_kg": 1}
                     ).status_code == 409
    anon.post(f"/api/hub/runs/{r['id']}/collect")
    done = anon.post(f"/api/hub/runs/{r['id']}/close", json={
        "hub_kg": r["expected_kg"], "facility_kg": r["expected_kg"]}
    ).json()
    assert done["record"] and not done["mismatch"]
    v = anon.get(f"/api/records/{done['record']}").json()
    assert v["valid"] and v["chain_ok"]
    pdf = anon.get(f"/api/records/{done['record']}/pdf")
    assert pdf.content[:4] == b"%PDF"
    login(anon, BIZ)
    csv = anon.get("/api/business/report.csv").text
    assert csv.startswith("record,closed")


def test_lot_and_pickup_details(anon):
    login(anon, BIZ)
    anon.post("/api/business/lots", json={
        "item": "vegetables", "condition": "overripe", "qty_kg": 3})
    lots = anon.get("/api/business/lots").json()
    waiting = next(x for x in lots if x["status"] == "waiting")
    d = anon.get(f"/api/business/lots/{waiting['id']}").json()
    assert d["reason"] and d["route"] and "match" in d and "matches" not in d
    planned = next(x for x in lots if x["status"] == "planned")
    d = anon.get(f"/api/business/lots/{planned['id']}").json()
    p = d["pickup"]
    assert p["facility"] and p["your_kg"] > 0 and p["lots"]
    assert all("name" not in str(s) for s in [p.get("pickup_from")] if s)
    assert anon.get(f"/api/business/pickups/{p['id']}").status_code == 200
    # another business can't open it, nor someone else's lot
    login(anon, BIZ2)
    assert anon.get(f"/api/business/lots/{planned['id']}").status_code == 404
    assert anon.get(f"/api/business/pickups/{p['id']}"
                    ).status_code == 404


def test_admin_flow(anon):
    login(anon, ADMIN)
    ov = anon.get("/api/admin/overview").json()
    assert ov["orgs"] >= 2 and set(ov["users"]) <= {
        "business", "hub", "admin"}
    pend = anon.get("/api/admin/orgs?status=pending").json()
    assert any("Manufacturing" in o["name"] for o in pend)
    bad = {"name": "Compost X", "kind": "compost", "tiers": "D",
           "lat": 28.5, "lng": 77.4, "capacity_kg": 100}
    assert anon.post("/api/admin/facilities", json=bad).status_code == 422
    bad.update(certified=True, cert_no="CERT-1")
    assert anon.post("/api/admin/facilities", json=bad).status_code == 200


def test_reset_flow_and_pw_change(anon):
    j = anon.post("/api/auth/forgot", json={"identifier": BIZ2}).json()
    code = j["dev_code"]
    assert anon.post("/api/auth/reset", json={
        "identifier": BIZ2, "code": "000000",
        "new_password": "Newpass123"}).status_code == 422
    assert anon.post("/api/auth/reset", json={
        "identifier": BIZ2, "code": code,
        "new_password": "Newpass123"}).status_code == 200
    login(anon, BIZ2, "Newpass123")


def test_shell_and_headers(anon):
    r = anon.get("/")
    assert r.status_code == 200
    assert "frame-ancestors" in r.headers["content-security-policy"]
    assert anon.get("/healthz").json()["ok"]
    # cross-site writes are blocked
    r = anon.post("/api/auth/logout", headers={"origin": "https://evil.x"})
    assert r.status_code == 403
