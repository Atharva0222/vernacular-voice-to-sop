import hashlib
import hmac
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import db
from app.config import settings

_bearer = HTTPBearer()


def _sign(person_id: int) -> str:
    return hmac.new(settings.auth_secret.encode(), str(person_id).encode(), hashlib.sha256).hexdigest()


def issue_token(person_id: int) -> str:
    return f"{person_id}.{_sign(person_id)}"


def current_person(creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)]) -> dict:
    """Resolve a bearer token to its people row. Role is read live, so a role change applies at once."""
    person_id, _, sig = creds.credentials.partition(".")
    if not person_id.isdigit() or not hmac.compare_digest(sig, _sign(int(person_id))):
        raise HTTPException(401, "invalid token")
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
