import json
import re
from pathlib import Path

import pytest

from app import compliance as C
from app.compliance import ask_compliance_copilot as ask
from conftest import login

DATA = Path(__file__).resolve().parent.parent / "app" / "data"
ROTI, SWILL = "FSSAI-FEED-GAUSHALA-ROTI", "FSSAI-FEED-2021-SWILL"
C3, C4, C5 = "FSSAI-SURPLUS-2019-C3", "FSSAI-SURPLUS-2019-C4", "FSSAI-SURPLUS-2019-C5"
R4, R14, BWG = "CPCB-SWM-2016-R4", "CPCB-SWM-2016-R14", "CPCB-BIO-2016-BWG"
S59, UCO, PKG, COLD = "FSSA-2006-SEC59", "FSSAI-RUCO-2018-UCO", "CPCB-PWM-2021-PKG", "FSSAI-COLD-2020-TRANSIT"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """These tests check the built-in engine, never the Gemini API."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


# ---------- off-topic questions are not answered with a random rule ----------
@pytest.mark.parametrize("q", [
    "can i eat a pencil?", "what is the capital of france", "how do I bake a cake", "what is 2+2",
    "write a poem about the moon", "how to cook dal", "recipe for roti", "olive oil price",
    "kya main pencil kha sakta hoon", "पेंसिल खा सकते हैं?", "मुझे कोई कहानी सुनाओ", "weather in delhi tomorrow",
])
def test_off_topic_gets_a_clear_message_and_no_fake_citations(q):
    r = ask(q)
    assert r["source"] == "out_of_scope"
    assert r["citations"] == []
    assert "Legal Assessment" not in r["answer"]
    assert ("outside what I can help with" in r["answer"]) or ("दायरे से बाहर" in r["answer"])


def test_off_topic_message_matches_the_language_of_the_question():
    assert re.search(r"[ऀ-ॿ]", ask("पेंसिल खा सकते हैं?")["answer"])
    assert re.search(r"[ऀ-ॿ]", ask("kya main pencil kha sakta hoon")["answer"])   # Hinglish -> Hindi
    assert not re.search(r"[ऀ-ॿ]", ask("can i eat a pencil?")["answer"])


@pytest.mark.parametrize("q", ["hi", "hello", "namaste", "नमस्ते"])
def test_greetings_get_a_welcome(q):
    r = ask(q)
    assert r["source"] == "greeting" and r["citations"] == []


# ---------- Hindi, Hinglish and Devanagari questions find the right rule ----------
@pytest.mark.parametrize("q,ok", [
    ("baasi roti gaay ko khila sakte hain?", {ROTI}),
    ("gaushala me roti de sakte hain kya", {ROTI}),
    ("kharab dahi ka kya karna chahiye", {C5}),
    ("expiry date nikal gayi to kya karu", {C5}),
    ("geela kachra kahan phenken", {R4, R14, BWG}),
    ("jurmana kitna lagta hai agar kharab khana becha", {S59}),
    ("purana tel ka kya karen", {UCO}),
    ("pakka hua khana kitni der tak rakh sakte hain", {C4}),
    ("khane ka kachra mix karke plastic ke saath phenk sakte hain", {R4, PKG}),
    ("बासी रोटी गाय को खिला सकते हैं?", {ROTI}),
    ("एक्सपायर्ड दूध का क्या करें", {C5}),
    ("जुर्माना कितना लगता है", {S59}),
    ("गीला कचरा कहाँ फेंकें", {R4, R14, BWG}),
    ("पुराना तेल कहाँ दें", {UCO}),
    ("दूध की गाड़ी का फ्रिज खराब हो गया तो क्या करें", {COLD, C4}),
    ("बचा हुआ खाना गरीबों को दे सकते हैं क्या", {C3, C4}),
])
def test_hindi_questions_find_the_right_rule(q, ok):
    top = ask(q)["citations"][0]["id"]
    assert top in ok, (q, top)


def test_english_questions_still_find_the_right_rule():
    for q, ok in [
        ("Can I feed expired bread to cows?", {SWILL, ROTI, C5}),
        ("What are the penalties under FSSAI Section 59?", {S59}),
        ("How long can cooked food stay at room temperature?", {C4}),
        ("Can I pour fryer oil down the drain?", {UCO}),
    ]:
        assert ask(q)["citations"][0]["id"] in ok, q


# ---------- the shape of an answer ----------
def test_english_answer_is_direct_first_then_quotes_the_rule():
    a = ask("Can I donate expired milk to an orphanage?")["answer"]
    assert a.startswith("Short answer:")
    assert "The rule says:" in a and "Source:" in a
    assert a.index("Short answer:") < a.index("The rule says:")


def test_hindi_question_gets_a_hindi_answer_with_the_english_rule_name():
    a = ask("बासी रोटी गाय को खिला सकते हैं?")["answer"]
    assert a.startswith("संक्षिप्त उत्तर:")
    assert "नियम:" in a and "Clause 4.2" in a


def test_cites_only_relevant_rules():
    r = ask("What are the penalties under FSSAI Section 59?")
    assert r["citations"][0]["id"] == S59 and len(r["citations"]) <= 3


# ---------- the data files ----------
def test_every_regulation_has_english_and_hindi_summaries():
    regs = json.load(open(DATA / "regulations.json", encoding="utf-8"))
    sm = json.load(open(DATA / "answer_summaries.json", encoding="utf-8"))
    for r in regs:
        e = sm.get(r["id"])
        assert e, f"no summary for {r['id']}"
        assert len(e["short"]) > 40 and re.search(r"[ऀ-ॿ]", e["short_hi"])
        assert re.search(r"[ऀ-ॿ]", e["action_hi"])


def test_word_table_is_well_formed():
    t = json.load(open(DATA / "hindi_terms.json", encoding="utf-8"))
    for section in ("terms", "prefixes", "phrases"):
        for k, v in t[section].items():
            assert k and isinstance(v, list) and v and all(isinstance(x, str) and x for x in v), (section, k)
    assert len(t["terms"]) > 200


def test_the_regulations_file_itself_is_untouched_by_the_extra_data():
    """Summaries and words live in their own files; the legal text stays as published."""
    regs = json.load(open(DATA / "regulations.json", encoding="utf-8"))
    assert all("short" not in r and "short_hi" not in r for r in regs)


# ---------- through the API, as the chat button uses it ----------
def test_api_off_topic_and_hindi(anon):
    login(anon, "9000000005")
    r = anon.post("/api/compliance/ask", json={"question": "can i eat a pencil?"})
    assert r.status_code == 200 and r.json()["source"] == "out_of_scope" and r.json()["citations"] == []
    r = anon.post("/api/compliance/ask", json={"question": "गौशाला में रोटी दे सकते हैं"})
    assert r.status_code == 200
    d = r.json()
    assert d["citations"][0]["id"] == ROTI and d["answer"].startswith("संक्षिप्त उत्तर:")
    assert C.DOMAIN_TERMS                          # the topic vocabulary loaded
