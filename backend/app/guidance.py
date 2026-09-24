import json

from app import llm
from app.schemas import Guidance, StoredStep

SYSTEM_PROMPT = """A factory worker has spoken into the machine's SOP page: a problem, a
question, or an account of what they did. You are given the machine's SOP cards, each with an
id, and the worker's transcribed speech, which may be messy, code-mixed, or repetitive.

Decide one thing only: do the SOP cards already tell the worker what to do?

- covered_by_sop = true when the answer is written on a card: the worker skipped a step, did
  steps in the wrong order, ignored a safety warning, or asks something a card already states.
  Then write the answer as a short spoken reminder, in the worker's language, saying what the
  SOP says to do. Two or three sentences, plain and respectful, no blame. Quote the card's
  instruction in your own words.
- covered_by_sop = false when the cards do not answer it: the machine is broken or unsafe, a
  card looks wrong, or the worker asks about something the SOP never mentions. Then answer is
  null, and a human will handle it.

Return strict JSON only, in this schema:
{ "covered_by_sop": boolean,
  "answer": string | null,   // the spoken reminder, in the worker's language; null when not covered
  "step_id": int | null }    // id of the card it concerns, or null if none fits

Never invent an instruction that is not on a card. If in doubt, covered_by_sop is false."""


def _user_message(steps: list[StoredStep], text: str, language: str) -> str:
    cards = [{"id": s.id, "step_number": s.step_number, "text": s.text,
              "is_safety_warning": s.is_safety_warning} for s in steps]
    return (f"Worker language: {language}\nSOP cards:\n{json.dumps(cards, ensure_ascii=False)}"
            f"\n\nWorker said:\n{text}")


async def answer_from_sop(steps: list[StoredStep], text: str, language: str) -> Guidance:
    """Answer a worker from their own SOP, or report that the SOP does not cover it."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _user_message(steps, text, language)},
    ]
    result = await llm.call_json(messages, Guidance)
    if result.step_id not in {s.id for s in steps}:
        result.step_id = None
    if not result.answer:
        result.covered_by_sop = False
    return result
