from conftest import login

BIZ = "9000000005"


def test_chat_files_are_served_and_loaded(anon):
    html = anon.get("/").text
    assert "/static/js/chat.js" in html
    assert html.index("/static/js/core.js") < html.index("/static/js/chat.js")
    js = anon.get("/static/js/chat.js").text
    assert "chatMount" in js and "/api/compliance/ask" in js


def test_business_can_ask_the_assistant_and_guests_cannot(anon):
    r = anon.post("/api/compliance/ask", json={"question": "cattle feed?"})
    assert r.status_code == 401
    login(anon, BIZ)
    r = anon.post("/api/compliance/ask",
                  json={"question": "Can expired food go to cattle feed?"})
    assert r.status_code == 200
    assert r.json()["answer"]
