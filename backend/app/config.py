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

    # Database - Supabase Postgres. database_url is the connection the app uses at request
    # time (point this at Supavisor in session mode, not transaction mode - transaction-mode
    # pooling breaks psycopg3's prepared-statement cache). database_migrate_url is the direct,
    # unpooled connection Alembic uses for DDL; defaults to database_url if unset (e.g. local dev
    # against `supabase start`, which has no pooler).
    database_url: str
    database_migrate_url: str | None = None

    # Auth - Supabase Auth. Staff sign in against Supabase directly from the frontend;
    # current_person() verifies the resulting JWT locally against Supabase's published JWKS
    # (supabase_url + "/auth/v1/.well-known/jwks.json" - current Supabase projects sign access
    # tokens with a per-project ES256 key, not a shared HS256 secret, so there is nothing secret
    # to configure here: the verification key is public by design). Keys are cached in-process
    # after the first fetch, so most requests still verify with no network round-trip.
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str  # RLS-bypassing - worker routes + Storage admin ops only

    storage_resume_bucket: str = "candidate-resumes"

    cors_origins: list[str] = []  # the preview is same-origin and needs none

    class Config:
        env_prefix = "V2S_"
        env_file = ".env"


settings = Settings()
settings.database_migrate_url = settings.database_migrate_url or settings.database_url
settings.tmp_dir.mkdir(parents=True, exist_ok=True)
(settings.tmp_dir / "audio_cache").mkdir(parents=True, exist_ok=True)
