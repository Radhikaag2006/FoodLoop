import os

from app import config as C


def test_env_file_fills_gaps_but_never_overrides(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text(
        "# comment\n\nFL_TEST_A=one\nFL_TEST_B = \"two\"\n"
        "FL_TEST_C=from_file\nnot a pair\n", encoding="utf-8")
    for k in ("FL_TEST_A", "FL_TEST_B"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("FL_TEST_C", "from_real_env")
    C.load_env_file(str(f))
    assert os.environ["FL_TEST_A"] == "one"
    assert os.environ["FL_TEST_B"] == "two"
    assert os.environ["FL_TEST_C"] == "from_real_env"
    for k in ("FL_TEST_A", "FL_TEST_B"):
        monkeypatch.delenv(k, raising=False)


def test_missing_env_file_is_fine(tmp_path):
    C.load_env_file(str(tmp_path / "nope.env"))
