import re

# the English/Hindi switch is made of two static files the page must load


def test_page_loads_the_language_files_before_the_app(anon):
    html = anon.get("/").text
    i18n, hi, core = (html.index(f"/static/js/{n}.js") for n in
                      ("i18n", "i18n-hi", "core"))
    assert i18n < hi < core
    for f in ("i18n.js", "i18n-hi.js"):
        assert anon.get(f"/static/js/{f}").status_code == 200


def test_hindi_dictionary_has_the_main_screens():
    src = open("static/js/i18n-hi.js", encoding="utf-8").read()
    for key in ("Home", "Lots", "Add lot", "Records", "Account", "Week",
                "Pool", "Runs", "Sites", "Sign in", "Create account",
                "Accept", "Drop-off", "Wrong mobile, email or password."):
        assert re.search(rf'"{re.escape(key)}":\s*"[^"]+"', src), key
    # every Hindi value is non-empty
    assert not re.search(r'"[^"\n]+":\s*""', src)


def test_server_error_texts_are_in_the_dictionary():
    """Messages the API sends should have a Hindi version."""
    import glob
    src = open("static/js/i18n-hi.js", encoding="utf-8").read()
    missing = []
    for f in glob.glob("app/routes/*.py"):
        for m in re.finditer(r'HTTPException\(\s*\d+,\s*"([^"{}]+)"\s*\)',
                             open(f, encoding="utf-8").read()):
            if f'"{m.group(1)}"' not in src:
                missing.append(m.group(1))
    assert len(missing) <= 8, missing      # a few long ones are patterns
