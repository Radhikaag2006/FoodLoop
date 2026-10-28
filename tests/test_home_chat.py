from conftest import login

BIZ = "9000000005"


def test_chat_script_is_served_and_loads_last(anon):
    html = anon.get("/").text
    assert "/static/js/chat.js" in html
    # after every existing script, so nothing else can be affected by it
    assert html.index("/static/js/boot.js") < html.index("/static/js/chat.js")
    js = anon.get("/static/js/chat.js")
    assert js.status_code == 200
    body = js.text
    assert "#/b/home" in body                    # Home screen only
    assert "/api/compliance/ask" in body         # the same RAG as the assistant
    assert "Demo@1234" not in body


def test_chat_uses_the_same_rag_as_the_assistant_screen(anon):
    r = anon.post("/api/compliance/ask", json={"question": "cattle feed?"})
    assert r.status_code == 401                  # signed-in users only
    login(anon, BIZ)
    r = anon.post("/api/compliance/ask",
                  json={"question": "Can expired food go to cattle feed?"})
    assert r.status_code == 200
    d = r.json()
    assert d["answer"] and isinstance(d["citations"], list)
    assert {"authority", "clause"} <= set(d["citations"][0])
