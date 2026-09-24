from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import db
from app.config import settings
from app.routes import login, machine, report, sop, structure, transcribe, tts


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    yield


app = FastAPI(title="Vernacular Voice-to-SOP", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcribe.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(structure.router, prefix="/api")
app.include_router(sop.router, prefix="/api")
app.include_router(machine.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(login.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


class _RevalidatingStatic(StaticFiles):
    """Preview pages change often; without this browsers cache them heuristically and show a stale UI."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


_preview_dir = Path(__file__).resolve().parent.parent / "static_preview"
app.mount("/preview", _RevalidatingStatic(directory=_preview_dir, html=True), name="preview")
