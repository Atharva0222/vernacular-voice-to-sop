from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app import tts
from app.limiter import limiter
from app.schemas import TTSRequest, TTSResponse

router = APIRouter()


@router.post("/tts", response_model=TTSResponse)
@limiter.limit("30/minute")
async def generate_tts(request: Request, req: TTSRequest) -> TTSResponse:
    if not req.text.strip():
        raise HTTPException(400, "text must not be empty")
    key, _path = await tts.synthesize(req.text, req.language)
    return TTSResponse(audio_url=f"/api/audio/{key}")


@router.get("/audio/{key}")
def get_audio(key: str):
    path = tts.cached_path_for_key(key)
    if not path.exists():
        raise HTTPException(404, "audio not found")
    return FileResponse(path, media_type="audio/mpeg")
