import pytest
from datetime import date, timedelta
from app.compliance import INDEX, check_lot_compliance, ask_compliance_copilot, get_all_regulations


def test_regulations_loaded():
    regs = get_all_regulations()
    assert len(regs) >= 5
    assert any("FSSAI" in r["authority"] for r in regs)
    assert any("CPCB" in r["authority"] or "MoEFCC" in r["authority"] for r in regs)


def test_bm25_search_retrieves_relevant_clauses():
    # Searching for temperature control
    results = INDEX.search("safe temperature holding cooked food", top_k=2)
    assert len(results) > 0
    top_doc = results[0][0]
    assert "FSSAI-SURPLUS-2019-C4" == top_doc["id"] or "Temperature" in top_doc["title"]

    # Searching for animal feed swill restriction
    feed_results = INDEX.search("cattle animal feed swill meat restriction", top_k=2)
    assert len(feed_results) > 0
    assert any("FEED" in r[0]["id"] or "Feed" in r[0]["title"] for r in feed_results)


def test_check_lot_compliance_expired():
    yesterday = date.today() - timedelta(days=1)
    res = check_lot_compliance("bread", condition="fresh", expiry_date=yesterday)
    assert res["status"] == "LOCKED_TO_RECOVERY"
    assert any(f["code"] == "EXPIRED_LOCK" for f in res["flags"])
    assert any(c["id"] == "FSSAI-SURPLUS-2019-C5" for c in res["citations"])


def test_check_lot_compliance_spoiled():
    res = check_lot_compliance("vegetables", condition="spoiled", expiry_date=None)
    assert res["status"] == "LOCKED_TO_RECOVERY"
    assert any(f["code"] == "SPOILAGE_LOCK" for f in res["flags"])


def test_check_lot_compliance_swill_feed_dairy():
    tomorrow = date.today() + timedelta(days=2)
    res = check_lot_compliance("dairy", condition="fresh", expiry_date=tomorrow)
    assert res["status"] == "RESTRICTED"
    assert any(f["code"] == "SWILL_FEED_RESTRICTION" for f in res["flags"])


def test_ask_compliance_copilot_offline():
    res = ask_compliance_copilot("What are the penalties under FSSAI Section 59 for unsafe food?")
    assert res["query"] != ""
    assert "Section 59" in res["answer"] or "penalties" in res["answer"].lower()
    assert len(res["citations"]) > 0


from tests.conftest import login


def test_compliance_api_routes(anon):
    login(anon, "9000000005")  # verified demo business

    # Test checking lot compliance via API
    r = anon.post(
        "/api/compliance/check",
        json={"item": "fruits", "condition": "spoiled", "expiry": None},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "LOCKED_TO_RECOVERY"
    assert len(data["citations"]) > 0

    # Test asking the copilot via API
    r2 = anon.post(
        "/api/compliance/ask",
        json={"question": "Can I feed expired food to cattle?"},
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert "answer" in data2
    assert len(data2["citations"]) > 0

    # Test listing regulations
    r3 = anon.get("/api/compliance/regulations")
    assert r3.status_code == 200
    assert len(r3.json()["regulations"]) >= 5
