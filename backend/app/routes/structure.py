from fastapi import APIRouter, HTTPException

from app import structuring
from app.schemas import SOPResponse, StructureRequest

router = APIRouter()


@router.post("/structure", response_model=SOPResponse)
async def structure_transcript(req: StructureRequest) -> SOPResponse:
    if not req.transcript.strip():
        raise HTTPException(400, "transcript must not be empty")
    try:
        return await structuring.structure_transcript(req.transcript)
    except Exception as exc:
        raise HTTPException(502, f"LLM structuring failed: {exc}") from exc
