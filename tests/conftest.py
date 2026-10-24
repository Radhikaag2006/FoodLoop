import os
import tempfile

import pytest

_d = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_d}/t.db"
os.environ["UPLOAD_DIR"] = f"{_d}/up"
os.environ["DEMO_MODE"] = "1"
os.environ["ENV"] = "development"
os.chdir(os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import security  # noqa: E402


@pytest.fixture(scope="session")
def boot():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def anon(boot):
    boot.cookies.clear()
    security._hits.clear()
    return boot


def login(c, phone, pw="Demo@1234"):
    c.cookies.clear()
    r = c.post("/api/auth/login", json={"identifier": phone,
                                        "password": pw})
    assert r.status_code == 200, r.text
    return r.json()
