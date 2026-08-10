import os
import tempfile
from pathlib import Path

# hf-xet (huggingface_hub's chunked transfer backend) hangs indefinitely on
# some networks; force plain HTTPS downloads instead. Must be set before any
# huggingface_hub/transformers import triggers a download.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Stage 1 - ASR
    asr_model_hi: str = "vasista22/whisper-hindi-medium"
    asr_model_mr: str = "steja/whisper-small-marathi"
    asr_lang_id_model: str = "openai/whisper-tiny"
    asr_device: str = "auto"  # auto | cpu | cuda | mps

    # Stage 2 - LLM (OpenAI-compatible endpoint, defaults to local Ollama)
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3.2:3b"
    llm_api_key: str = "ollama"  # Ollama ignores this, kept for OpenAI-compatible clients
    llm_timeout_seconds: float = 120.0

    # Stage 3 - TTS (confirmed available via `edge-tts --list-voices`)
    tts_voice_hi: str = "hi-IN-SwaraNeural"
    tts_voice_mr: str = "mr-IN-AarohiNeural"

    tmp_dir: Path = Path(tempfile.gettempdir()) / "voice-to-sop"

    class Config:
        env_prefix = "V2S_"
        env_file = ".env"


settings = Settings()
settings.tmp_dir.mkdir(parents=True, exist_ok=True)
(settings.tmp_dir / "audio_cache").mkdir(parents=True, exist_ok=True)
