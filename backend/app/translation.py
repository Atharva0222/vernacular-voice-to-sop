from app import llm
from app.schemas import Translation

_LANGUAGE_NAME = {"hi": "Hindi", "mr": "Marathi"}

SYSTEM_PROMPT = """You translate a factory manager's written reply so a line worker can hear it
spoken in their own language.

Rules:
- Translate into the target language only. Never reply in English or any other language.
- Use the Devanagari script, never transliteration.
- Keep it short and spoken-sounding: this is read aloud by a text-to-speech voice, not read off
  a screen. Two or three plain sentences at most.
- Keep machine names, part numbers, measurements and units exactly as written.
- Be respectful and direct. Do not add advice, blame or pleasantries the manager did not write.
- If the reply is already in the target language, return it cleaned up, not re-worded.

Return strict JSON only: { "text": string }"""


async def to_worker_language(reply: str, language: str) -> str:
    """Translate a manager's reply into the worker's language for TTS playback.

    Falls back to the manager's own text if the language is not one we voice, so a reply is
    never silently dropped.
    """
    target = _LANGUAGE_NAME.get(language)
    if not target:
        return reply
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Target language: {target}\n\nManager wrote:\n{reply}"},
    ]
    result = await llm.call_json(messages, Translation)
    return result.text.strip() or reply
