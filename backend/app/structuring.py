from app import llm
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

async def structure_transcript(transcript: str) -> SOPResponse:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": transcript},
    ]
    return await llm.call_json(messages, SOPResponse)
