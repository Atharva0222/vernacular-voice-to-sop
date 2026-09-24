import json
import re

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

_RETRY_NUDGE = (
    "Your previous output was not valid JSON matching the schema. "
    "Return ONLY valid JSON, no markdown, no explanation."
)


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


async def call_json[T: BaseModel](messages: list[dict], model_cls: type[T]) -> T:
    """Call the LLM and validate its JSON reply as model_cls, retrying once with a nudge."""
    content = await _call_llm(messages)
    try:
        return model_cls.model_validate(_extract_json(content))
    except (json.JSONDecodeError, ValidationError):
        pass

    retry = [*messages, {"role": "assistant", "content": content}, {"role": "user", "content": _RETRY_NUDGE}]
    content = await _call_llm(retry)
    return model_cls.model_validate(_extract_json(content))
