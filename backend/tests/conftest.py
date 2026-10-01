import os

# Must be set before `app.config` is imported by anything below, since Settings() is
# instantiated at module import time and will crash without an auth secret.
os.environ.setdefault("V2S_AUTH_SECRET", "test-secret-do-not-use-in-prod")
os.environ.setdefault("V2S_LLM_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.limiter import limiter
from app.main import app


@pytest.fixture()
def client(tmp_path):
    """A TestClient against a fresh, seeded, per-test SQLite file.

    Settings is a process-wide singleton, so pointing db_path at a temp file before the
    TestClient's lifespan runs db.init() is what isolates each test's data. The rate
    limiter's in-memory store is also process-wide, so it needs the same per-test reset
    or an early test's requests count against a later test's budget.
    """
    settings.db_path = tmp_path / "test.db"
    limiter.reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def conn(client):
    """A raw connection into the same per-test database the client fixture just seeded."""
    with db.connect() as connection:
        yield connection


# id -> PIN for the demo org seeded by db.init() (see app/db.py DEMO_PINS).
DEMO_PINS = {1: "1111", 2: "2222", 3: "3333", 4: "4444", 5: "5555"}


def login(client: TestClient, person_id: int) -> str:
    resp = client.post("/api/login", json={"person_id": person_id, "pin": DEMO_PINS[person_id]})
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def auth_headers(client: TestClient, person_id: int) -> dict:
    return {"Authorization": f"Bearer {login(client, person_id)}"}
