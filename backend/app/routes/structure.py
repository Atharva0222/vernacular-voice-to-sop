from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app import auth, structuring
from app.schemas import SOPResponse, StructureRequest

router = APIRouter()
Author = Annotated[dict, Depends(auth.sop_author)]


@router.post("/structure", response_model=SOPResponse)
async def structure_transcript(req: StructureRequest, person: Author) -> SOPResponse:
    if not req.transcript.strip():
        raise HTTPException(400, "transcript must not be empty")
    try:
        return await structuring.structure_transcript(req.transcript)
    except Exception as exc:
        raise HTTPException(502, f"LLM structuring failed: {exc}") from exc
