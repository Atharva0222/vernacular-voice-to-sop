import hmac

from fastapi import APIRouter, HTTPException

from app import auth, db
from app.config import settings
from app.schemas import LoginRequest, LoginResponse

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    """Issue a token for a person, gated by the server-side secret. No per-user passwords yet."""
    if not hmac.compare_digest(req.secret, settings.auth_secret):
        raise HTTPException(401, "wrong secret")
    with db.connect() as conn:
        person = conn.execute("SELECT id, name, role FROM people WHERE id = ?", (req.person_id,)).fetchone()
    if not person:
        raise HTTPException(404, "person not found")
    return LoginResponse(token=auth.issue_token(person["id"]), name=person["name"], role=person["role"])
