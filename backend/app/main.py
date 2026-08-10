from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import structure, transcribe, tts

app = FastAPI(title="Vernacular Voice-to-SOP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcribe.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(structure.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


_preview_dir = Path(__file__).resolve().parent.parent / "static_preview"
app.mount("/preview", StaticFiles(directory=_preview_dir, html=True), name="preview")
