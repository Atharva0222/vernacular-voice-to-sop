import hashlib
import hmac
import os
import time
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import db
from app.config import settings

# auto_error off so a missing token is a 401, not FastAPI's default 403 - the frontend
# needs to tell "not signed in" apart from "signed in but not allowed".
_bearer = HTTPBearer(auto_error=False)
_SESSION_SECONDS = 12 * 3600
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def hash_pin(pin: str) -> str:
    """Scramble a PIN with scrypt and a fresh salt, stored as salt_hex$hash_hex."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(pin.encode(), salt=salt, **_SCRYPT)
    return f"{salt.hex()}${digest.hex()}"


def verify_pin(pin: str, stored: str | None) -> bool:
    """Check a PIN against a stored hash. A person with no PIN can never sign in."""
    if not stored or "$" not in stored:
        return False
    salt_hex, _, digest_hex = stored.partition("$")
    digest = hashlib.scrypt(pin.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _sign(body: str) -> str:
    return hmac.new(settings.auth_secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def issue_token(person_id: int) -> str:
    """A signed token that expires, so a lost session does not stay valid forever."""
    body = f"{person_id}.{int(time.time()) + _SESSION_SECONDS}"
    return f"{body}.{_sign(body)}"


def current_person(creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> dict:
    """Resolve a bearer token to its people row. Role is read live, so a role change applies at once."""
    if creds is None:
        raise HTTPException(401, "sign in first")
    person_id, _, rest = creds.credentials.partition(".")
    expires, _, sig = rest.partition(".")
    if not person_id.isdigit() or not expires.isdigit():
        raise HTTPException(401, "invalid token")
    if not hmac.compare_digest(sig, _sign(f"{person_id}.{expires}")):
        raise HTTPException(401, "invalid token")
    if int(expires) < time.time():
        raise HTTPException(401, "session expired")
    with db.connect() as conn:
        person = conn.execute("SELECT id, name, role, plant_id FROM people WHERE id = ?", (person_id,)).fetchone()
    if not person:
        raise HTTPException(401, "invalid token")
    return dict(person)


def report_reader(person: Annotated[dict, Depends(current_person)]) -> dict:
    """Managers and plant heads only. Supervisors never see worker reports."""
    if person["role"] == "supervisor":
        raise HTTPException(403, "supervisors cannot access worker reports")
    return person


def scope_sql(person: dict) -> tuple[str, dict]:
    """WHERE clause over a view with line_id/plant_id limiting a reader to their own lines, or their plant for a plant head."""
    if person["role"] == "plant_head":
        return "plant_id = :viewer_plant", {"viewer_plant": person["plant_id"]}
    return "line_id IN (SELECT id FROM lines WHERE manager_id = :viewer)", {"viewer": person["id"]}


def sop_author(person: Annotated[dict, Depends(current_person)]) -> dict:
    """Any signed-in staff member may author. Which lines they may touch is checked per route."""
    return person


def may_author_line(person: dict, line_id: int, conn) -> bool:
    """A plant head covers their whole plant; anyone else only the lines they run."""
    if person["role"] == "plant_head":
        row = conn.execute("SELECT 1 FROM lines WHERE id = ? AND plant_id = ?", (line_id, person["plant_id"])).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM lines WHERE id = ? AND (supervisor_id = ? OR manager_id = ?)",
            (line_id, person["id"], person["id"]),
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
