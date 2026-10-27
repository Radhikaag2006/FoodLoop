import os

from conftest import login

PHOTO_DIR = os.path.join("static", "img", "items")


def test_catalog_offers_a_photo_only_when_one_exists(anon):
    os.makedirs(PHOTO_DIR, exist_ok=True)
    path = os.path.join(PHOTO_DIR, "fruits.png")
    assert not os.path.exists(path)              # nothing shipped by default
    try:
        items = {i["key"]: i for i in anon.get("/api/catalog").json()["items"]}
        assert items["fruits"]["image"] == ""     # drawings are the default
        with open(path, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n")
        items = {i["key"]: i for i in anon.get("/api/catalog").json()["items"]}
        assert items["fruits"]["image"] == "/static/img/items/fruits.png"
        assert items["dairy"]["image"] == ""      # others are unaffected
        assert anon.get(items["fruits"]["image"]).status_code == 200
    finally:
        if os.path.exists(path):
            os.remove(path)
