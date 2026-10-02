from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from app import db
from app.config import settings

# auto_error off so a missing token is a 401, not FastAPI's default 403 - the frontend
# needs to tell "not signed in" apart from "signed in but not allowed".
_bearer = HTTPBearer(auto_error=False)

# Current Supabase projects sign access tokens with a per-project ES256 key and publish the
# matching public key at this well-known JWKS URL - there is no shared secret to configure.
# PyJWKClient fetches and caches keys by `kid` in-process, re-fetching only on a cache miss
# (e.g. after key rotation), so most requests verify with no network round-trip.
_jwks_client = jwt.PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")


def current_person(creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> dict:
    """Resolve a Supabase Auth JWT to its employees row. Verified locally on every request - no
    session cache - so a role change in `employees` applies at once, the same property the old
    HMAC tokens had. Supabase owns issuing and expiring the token; this only checks it is
    genuine, unexpired, and has a matching `profiles` row."""
    if creds is None:
        raise HTTPException(401, "sign in first")
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(creds.credentials)
        claims = jwt.decode(creds.credentials, signing_key.key, algorithms=["ES256", "RS256"], audience="authenticated")
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid token") from None
    auth_uid = claims["sub"]
    with db.connect(auth_uid) as conn:
        person = conn.execute(
            text(
                "SELECT e.id, e.name, e.role, e.plant_id FROM employees e "
                "JOIN profiles p ON p.employee_id = e.id WHERE p.id = :uid"
            ),
            {"uid": auth_uid},
        ).mappings().fetchone()
    if not person:
        raise HTTPException(401, "no employee profile for this account")
    return {**person, "_auth_uid": auth_uid}


def report_reader(person: Annotated[dict, Depends(current_person)]) -> dict:
    """Managers and plant heads only - an allow-list, not a supervisor-only deny-list, since
    the role set has grown past the original three (hr_admin/recruiter have no business here
    either)."""
    if person["role"] not in ("manager", "plant_head"):
        raise HTTPException(403, "only managers and plant heads may access worker reports")
    return person


def scope_sql(person: dict) -> tuple[str, dict]:
    """WHERE clause over a view with line_id/plant_id limiting a reader to their own lines, or their plant for a plant head."""
    if person["role"] == "plant_head":
        return "plant_id = :viewer_plant", {"viewer_plant": person["plant_id"]}
    return "line_id IN (SELECT id FROM lines WHERE manager_id = :viewer)", {"viewer": person["id"]}


def sop_author(person: Annotated[dict, Depends(current_person)]) -> dict:
    """Any signed-in staff member may author. Which lines they may touch is checked per route."""
    return person


def recruiter_access(person: Annotated[dict, Depends(current_person)]) -> dict:
    """Recruitment pipeline writes: hr_admin, recruiter, or plant_head."""
    if person["role"] not in ("hr_admin", "recruiter", "plant_head"):
        raise HTTPException(403, "only HR admins, recruiters, and plant heads may manage recruitment")
    return person


def org_admin(person: Annotated[dict, Depends(current_person)]) -> dict:
    """Plant-wide org config writes (employee directory, departments, shift definitions):
    hr_admin or plant_head only."""
    if person["role"] not in ("hr_admin", "plant_head"):
        raise HTTPException(403, "only HR admins and plant heads may manage plant-wide org settings")
    return person


def may_author_line(person: dict, line_id: int, conn) -> bool:
    """A plant head covers their whole plant; anyone else only the lines they run."""
    if person["role"] == "plant_head":
        row = conn.execute(
            text("SELECT 1 FROM lines WHERE id = :line_id AND plant_id = :plant_id"),
            {"line_id": line_id, "plant_id": person["plant_id"]},
        ).fetchone()
    else:
        row = conn.execute(
            text("SELECT 1 FROM lines WHERE id = :line_id AND (supervisor_id = :pid OR manager_id = :pid)"),
            {"line_id": line_id, "pid": person["id"]},
        ).fetchone()
    return row is not None


def author_scope_sql(person: dict) -> tuple[str, dict]:
    """WHERE clause over a view with line_id/plant_id limiting an author to the lines they run."""
    if person["role"] == "plant_head":
        return "plant_id = :author_plant", {"author_plant": person["plant_id"]}
    return (
        "line_id IN (SELECT id FROM lines WHERE supervisor_id = :author OR manager_id = :author)",
        {"author": person["id"]},
    )
