from fastapi import APIRouter, HTTPException, Request

from app import auth, db
from app.limiter import limiter
from app.schemas import LoginRequest, LoginResponse

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(request: Request, req: LoginRequest) -> LoginResponse:
    """Issue a session token for a person who knows their own PIN."""
    with db.connect() as conn:
        person = conn.execute(
            "SELECT id, name, role, pin_hash FROM people WHERE id = ?", (req.person_id,)
        ).fetchone()
    # One message for both cases, so valid person ids cannot be discovered by guessing.
    if not person or not auth.verify_pin(req.pin, person["pin_hash"]):
        raise HTTPException(401, "wrong id or PIN")
    return LoginResponse(token=auth.issue_token(person["id"]), name=person["name"], role=person["role"])
