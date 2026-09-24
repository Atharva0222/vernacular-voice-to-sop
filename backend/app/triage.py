import json

from app import llm
from app.schemas import StoredStep, Triage

SYSTEM_PROMPT = """A factory worker has spoken a short complaint about the machine they work
on. You are given the SOP (standard operating procedure) cards for that machine, each with an
id, and the worker's transcribed speech, which may be messy, code-mixed, or repetitive.

Decide what the real problem is:
- "machine": the equipment itself is faulty or unsafe (loose part, leak, noise, broken guard).
  The SOP is fine; the machine needs repair.
- "sop": the SOP card is wrong or missing something (wrong bolt size, wrong setting, a step
  that does not match reality). The card needs to change.
- "understanding": the SOP is correct but the worker is confused by it or does steps in the
  wrong order. Training is needed, not a card or machine change.

Return strict JSON only, in this schema:
{ "kind": "machine" | "sop" | "understanding",
  "summary": string,          // the complaint as one clean, plain paragraph, in the worker's language
  "step_id": int | null,      // id of the SOP step it concerns, or null if none fits
  "severity": "low" | "medium" | "high",   // high = risk of injury or of stopping the line
  "suggested_change": string | null }      // for kind "sop": the corrected step text; else null

Write the summary in the worker's language. Do not add facts the worker did not say."""


def _user_message(steps: list[StoredStep], text: str, language: str, step_hint: int | None) -> str:
    cards = [{"id": s.id, "step_number": s.step_number, "text": s.text} for s in steps]
    hint = f"\nThe worker pressed the report button on step id {step_hint}." if step_hint else ""
    return f"Worker language: {language}\nSOP steps:\n{json.dumps(cards, ensure_ascii=False)}{hint}\n\nWorker said:\n{text}"


async def triage(steps: list[StoredStep], text: str, language: str, step_hint: int | None) -> Triage:
    """Classify a worker complaint against its SOP; drop a step_id that is not one of the SOP's steps."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _user_message(steps, text, language, step_hint)},
    ]
    result = await llm.call_json(messages, Triage)
    if result.step_id not in {s.id for s in steps}:
        result.step_id = None
    return result
