import hashlib

import edge_tts

from app.config import settings

_VOICE_BY_LANG = {
    "hi": settings.tts_voice_hi,
    "mr": settings.tts_voice_mr,
}


def _cache_path(text: str, voice: str):
    key = hashlib.sha256(f"{voice}::{text}".encode()).hexdigest()
    return settings.tmp_dir / "audio_cache" / f"{key}.mp3", key


async def synthesize(text: str, language: str) -> tuple[str, str]:
    """Returns (cache_key, file_path). Cached on disk by hash(voice+text)."""
    voice = _VOICE_BY_LANG[language]
    path, key = _cache_path(text, voice)
    if not path.exists():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(path))
    return key, str(path)


def cached_path_for_key(key: str):
    return settings.tmp_dir / "audio_cache" / f"{key}.mp3"
