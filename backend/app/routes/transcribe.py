import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app import asr
from app.config import settings
from app.schemas import TranscribeResponse

router = APIRouter()

_ALLOWED_LANGS = {"hi", "mr", "auto"}


@router.post("/transcribe", response_model=TranscribeResponse)
def transcribe_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = Form("auto"),
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
