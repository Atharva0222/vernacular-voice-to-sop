import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import auth
from app.config import settings
from app.limiter import limiter
from app.logging_config import configure_logging
from app.observability import observability_middleware
from app.routes import employees, leave, machine, recruitment, report, sop, structure, transcribe, tts, workforce

configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Schema is Alembic-managed now (`alembic upgrade head`), not created on boot - a shared
    # hosted Postgres instance isn't a per-dev SQLite file, so DDL only happens explicitly.
    yield


app = FastAPI(title="Vernacular Voice-to-SOP", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Outermost middleware, so a 429 or CORS rejection is still counted and logged.
app.middleware("http")(observability_middleware)

app.mount("/metrics", make_asgi_app())

app.include_router(transcribe.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(structure.router, prefix="/api")
app.include_router(sop.router, prefix="/api")
app.include_router(machine.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(employees.router, prefix="/api")
app.include_router(workforce.router, prefix="/api")
app.include_router(leave.router, prefix="/api")
app.include_router(recruitment.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/me")
def me(person: Annotated[dict, Depends(auth.current_person)]) -> dict:
    """Role/name for the signed-in staff member, read live from `employees` on every call -
    the frontend session wrapper calls this instead of trusting anything cached client-side."""
    return {"name": person["name"], "role": person["role"]}


class _RevalidatingStatic(StaticFiles):
    """Preview pages change often; without this browsers cache them heuristically and show a stale UI."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


_preview_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _preview_dir.is_dir():
    app.mount("/preview", _RevalidatingStatic(directory=_preview_dir, html=True), name="preview")
else:
    # Pure-backend work (pytest, API-only dev) shouldn't require Node/npm to be installed.
    # StaticFiles raises at import time if the directory is missing, which would otherwise
    # take every /api route down with it.
    logging.getLogger(__name__).warning(
        "%s not found - /preview is unavailable. Run `npm install && npm run build` in frontend/.",
        _preview_dir,
    )
