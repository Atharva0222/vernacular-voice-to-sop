import json
import re

import httpx
from pydantic import ValidationError

from app.config import settings
from app.schemas import SOPResponse

SYSTEM_PROMPT = """You are converting a factory manager's spoken, unstructured procedure into
a clean SOP. The manager may explain steps out of order or repeat things.
Your job:
1. Identify the TRUE logical sequence of steps, regardless of the order
   they were mentioned in.
2. Break it into numbered, atomic steps (one action per step).
3. For each step, detect if it mentions a safety hazard (heat, sharp edges,
   electrical, chemicals, moving parts, or explicit warnings like 'be
   careful'). If yes, set is_safety_warning: true.
4. Suggest a simple icon keyword for each step (e.g. 'wear_gloves',
   'cut', 'heat', 'check', 'power_off').
5. Keep step text in the ORIGINAL language the manager used. Do not
   translate.
Output strict JSON only, in this schema:
{ "steps": [ { "step_number": int, "text": string,
  "is_safety_warning": bool, "icon": string } ] }"""

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(content: str) -> dict:
    fenced = _JSON_FENCE_RE.search(content)
    raw = fenced.group(1) if fenced else content
    return json.loads(raw)


async def _call_llm(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        resp = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": messages,
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def structure_transcript(transcript: str) -> SOPResponse:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": transcript},
    ]

    content = await _call_llm(messages)
    try:
        return SOPResponse.model_validate(_extract_json(content))
    except (json.JSONDecodeError, ValidationError):
        pass

    # one retry with an explicit nudge
    messages.append({"role": "assistant", "content": content})
    messages.append(
        {
            "role": "user",
            "content": "Your previous output was not valid JSON matching the schema. "
            "Return ONLY valid JSON, no markdown, no explanation.",
        }
    )
    content = await _call_llm(messages)
    return SOPResponse.model_validate(_extract_json(content))
