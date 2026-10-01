import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app import asr, auth
from app.config import settings
from app.limiter import limiter
from app.schemas import TranscribeResponse

router = APIRouter()
Author = Annotated[dict, Depends(auth.sop_author)]

_ALLOWED_LANGS = {"hi", "mr", "auto"}


@router.post("/transcribe", response_model=TranscribeResponse)
@limiter.limit("30/minute")
def transcribe_audio(
    request: Request,
    person: Author,
    audio: UploadFile = File(...),
    language: str | None = Form("auto"),
) -> TranscribeResponse:
    """Sync def so FastAPI dispatches this CPU-bound work to its threadpool
    instead of blocking the single asyncio event loop."""
    if language not in _ALLOWED_LANGS:
        raise HTTPException(400, f"language must be one of {_ALLOWED_LANGS}")

    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    tmp_path = settings.tmp_dir / f"upload-{uuid.uuid4().hex}{suffix}"
    try:
        content = audio.file.read()
        tmp_path.write_bytes(content)

        hint = None if language == "auto" else language
        transcript, detected_language = asr.transcribe(str(tmp_path), hint)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not transcript:
        raise HTTPException(422, "Transcription produced empty text - check audio quality/format")

    return TranscribeResponse(transcript=transcript, detected_language=detected_language)
