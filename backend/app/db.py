import json
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings

engine: Engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)


@contextmanager
def connect(identity: str | dict):
    """A connection scoped to one signed-in staff member, so RLS policies apply to every query
    run inside it. `identity` is either a Supabase auth user id (str - used by
    app.auth.current_person while it is still resolving whose id that is) or an already-resolved
    person dict carrying that id under "_auth_uid" (every other call site, once a route has its
    `person` dependency).

    Supabase's own RLS examples assume PostgREST as the client, which sets the acting Postgres
    role and the `request.jwt.claims` GUC automatically per request so `auth.uid()` resolves
    inside policies. A plain psycopg connection has to do both by hand, once per transaction -
    this is that hand-rolled equivalent, scoped to a single `engine.begin()` transaction so it
    never leaks onto a pooled connection reused by a different request.
    """
    auth_uid = identity if isinstance(identity, str) else identity["_auth_uid"]
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE authenticated"))
        # SET/SET LOCAL do not accept bind parameters (a Postgres protocol restriction, not a
        # SQLAlchemy one - verified directly against a local Supabase instance while building
        # this), so the claims JSON goes through set_config()'s third ("is_local") argument
        # instead, which is the parameterizable equivalent of SET LOCAL.
        conn.execute(
            text("SELECT set_config('request.jwt.claims', :claims, true)"),
            {"claims": json.dumps({"sub": auth_uid, "role": "authenticated"})},
        )
        yield conn


@contextmanager
def connect_service():
    """A connection that bypasses RLS entirely, for the handful of routes that are
    deliberately reachable with no identity at all: POST /report, POST /ask,
    GET /receipt/{receipt}, GET /machines, GET /machine/{id}/sop, and the background triage
    pipeline those kick off. Workers never get a Supabase session - this is the only path their
    traffic takes into Postgres, which keeps the backend's own rate limiting and triage pipeline
    as the sole gate on these tables rather than exposing them to Supabase's anon/PostgREST path.
    """
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE service_role"))
        yield conn
