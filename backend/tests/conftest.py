import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.limiter import limiter
from app.main import app

_PASSWORD = "test-password-do-not-use-in-prod"

# person_id -> (email, name, role) for the demo org every test reseeds, kept at the same ids
# the old SQLite DEMO_ORG used so test assertions (line_id=1, assigned_to=2, ...) still hold.
DEMO_PEOPLE = {
    1: ("person1@test.local", "Demo Supervisor", "supervisor"),
    2: ("person2@test.local", "Demo Manager", "manager"),
    3: ("person3@test.local", "Demo Plant Head", "plant_head"),
    4: ("person4@test.local", "Demo Supervisor B", "supervisor"),
    5: ("person5@test.local", "Demo Manager B", "manager"),
}

def _pg_dsn() -> str:
    # settings.database_url is a SQLAlchemy URL (postgresql+psycopg://...); psycopg wants plain libpq.
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def _signup_or_signin(http: httpx.Client, email: str) -> str:
    """Create the demo auth user the first time tests run against this Supabase instance; on
    later runs it already exists, so fall back to signing in to recover its id."""
    r = http.post("/auth/v1/signup", json={"email": email, "password": _PASSWORD})
    if r.status_code != 200:
        r = http.post("/auth/v1/token?grant_type=password", json={"email": email, "password": _PASSWORD})
        r.raise_for_status()
    return r.json()["user"]["id"]


@pytest.fixture(scope="session")
def demo_auth() -> dict[int, tuple[str, str]]:
    """person_id -> (auth uid, access token), set up once per test session.

    Signing up a Supabase user is comparatively slow, and the local token's 3600s expiry
    easily outlives a full test run, so there is no need to redo this per test - only the
    Postgres-side employees/profiles rows get reseeded per test (see `client` below)."""
    with httpx.Client(base_url=settings.supabase_url, headers={"apikey": settings.supabase_anon_key}) as http:
        result = {}
        for person_id, (email, _, _) in DEMO_PEOPLE.items():
            uid = _signup_or_signin(http, email)
            token = http.post(
                "/auth/v1/token?grant_type=password", json={"email": email, "password": _PASSWORD}
            ).json()["access_token"]
            result[person_id] = (uid, token)
        return result


@pytest.fixture()
def client(demo_auth):
    """A TestClient against a freshly reseeded demo org.

    Unlike the old SQLite setup (a fresh file per test), every test shares one local Supabase
    Postgres instance - isolation comes from truncating and reseeding the same fixed demo-org
    rows each test, not from a new database file. The rate limiter's in-memory store is still
    process-wide and needs the same per-test reset it always has.
    """
    admin = psycopg.connect(_pg_dsn(), autocommit=True)
    cur = admin.cursor()
    # TRUNCATE ... CASCADE rather than an ordered list of per-table DELETEs: a hand-maintained
    # order breaks every time a new module adds tables with their own FKs (hit twice already -
    # see the Employee and Workforce module migrations), where CASCADE just handles it.
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version'")
    tables = [r[0] for r in cur.fetchall()]
    if tables:
        cur.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")

    cur.execute("INSERT INTO plants (id, name) OVERRIDING SYSTEM VALUE VALUES (1, 'Demo Plant')")
    cur.execute(
        "INSERT INTO employees (id, name, role, language, plant_id) OVERRIDING SYSTEM VALUE VALUES "
        "(1, 'Demo Supervisor', 'supervisor', 'hi', 1), (2, 'Demo Manager', 'manager', 'hi', 1), "
        "(3, 'Demo Plant Head', 'plant_head', 'hi', 1), (4, 'Demo Supervisor B', 'supervisor', 'mr', 1), "
        "(5, 'Demo Manager B', 'manager', 'mr', 1)"
    )
    cur.execute(
        "INSERT INTO lines (id, plant_id, name, supervisor_id, manager_id) OVERRIDING SYSTEM VALUE VALUES "
        "(1, 1, 'Line A', 1, 2), (2, 1, 'Line B', 4, 5)"
    )
    cur.execute(
        "INSERT INTO machines (id, line_id, name) OVERRIDING SYSTEM VALUE VALUES (1, 1, 'Press 1'), (2, 2, 'Lathe 1')"
    )
    cur.executemany(
        "INSERT INTO profiles (id, employee_id) VALUES (%s, %s)",
        [(demo_auth[pid][0], pid) for pid in DEMO_PEOPLE],
    )
    # OVERRIDING SYSTEM VALUE doesn't advance the identity sequence, so a later auto-generated
    # insert (e.g. a test creating a new SOP) must not collide with the fixed demo ids above.
    for table, seq_max in (("plants", 1), ("employees", 5), ("lines", 2), ("machines", 2)):
        cur.execute(f"SELECT setval('{table}_id_seq', %s)", (seq_max,))
    admin.close()

    limiter.reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def conn(client):
    """A raw service-role connection (bypasses RLS) into the same seeded database, for tests
    that assert directly on rows rather than going through an authenticated route - the real
    app only ever runs this kind of direct SQL from service-role contexts too (background
    triage/routing), never from a specific signed-in person's connection."""
    with db.connect_service() as connection:
        yield connection


@pytest.fixture()
def auth_headers(demo_auth):
    """`auth_headers(person_id)` -> bearer header for that demo person's real Supabase session."""

    def _make(person_id: int) -> dict:
        return {"Authorization": f"Bearer {demo_auth[person_id][1]}"}

    return _make
