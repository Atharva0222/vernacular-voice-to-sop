# Vernacular Voice-to-SOP — Project Overview

## What the project is

A backend service that turns a factory manager's spoken, unstructured procedure in
**Hindi or Marathi** into a clean, numbered **Standard Operating Procedure (SOP)**,
and reads each step back as audio in the same language.

The pipeline has three stages:

1. **ASR** — upload/record audio, get a transcript plus the detected language.
2. **Structuring** — an LLM reorders the rambling speech into the true logical
   sequence of atomic steps, flags safety warnings, and suggests an icon keyword
   per step. Step text stays in the original language (no translation).
3. **TTS** — each step is synthesized back to speech in Hindi or Marathi.

A minimal browser preview page is bundled so the whole flow can be demoed without
a separate frontend.

## What it is based on

| Stage | Tech |
|---|---|
| API framework | FastAPI + Uvicorn (Python 3.12) |
| ASR (Hindi) | `vasista22/whisper-hindi-medium` (Hugging Face Transformers) |
| ASR (Marathi) | `steja/whisper-small-marathi` |
| Language ID | `openai/whisper-tiny` built-in language detection |
| Audio handling | librosa, soundfile, ffmpeg |
| LLM structuring | Any OpenAI-compatible chat endpoint — currently **Groq** (`gpt-oss-120b`); defaults to local Ollama if unset |
| TTS | `edge-tts` — voices `hi-IN-SwaraNeural` and `mr-IN-AarohiNeural` |
| Validation | Pydantic v2 + pydantic-settings |
| Deploy | Docker; configs for Render (`render.yaml`) and Railway (`railway.json`) |

Notable implementation details:

- The two Whisper fine-tunes ship a stale `generation_config` that breaks on modern
  `transformers`, so the base checkpoint's config (`whisper-medium` / `whisper-small`)
  is swapped in at load time.
- Those fine-tunes were trained on short clips, so long audio is split **on silence
  gaps** into ~25s windows (never mid-word) and transcribed window by window,
  instead of relying on Whisper's long-form/chunked stitching.
- `HF_HUB_DISABLE_XET=1` is forced because the Xet transfer backend hangs on some
  networks.
- Model weights are baked into the Docker image so cold starts don't re-download.
- TTS output is cached on disk by `sha256(voice + text)`.

## What code it is using

```
backend/
  app/
    main.py                  FastAPI app, CORS, router wiring, /preview static mount
    config.py                Settings (env prefix V2S_, reads backend/.env)
    schemas.py               Pydantic models (Step, SOPResponse, TTS, ...)
    asr.py                   Whisper load, language ID, silence-split transcription
    structuring.py           LLM prompt + JSON extraction + one retry on bad JSON
    tts.py                   edge-tts synthesis with on-disk cache
    routes/
      transcribe.py          POST /api/transcribe
      structure.py           POST /api/structure
      tts.py                 POST /api/tts, GET /api/audio/{key}
  static_preview/index.html  Demo UI (Tailwind CDN + lucide icons)
  Dockerfile                 python:3.12-slim + ffmpeg, pre-downloads models
  requirements.txt
  railway.json
render.yaml
```

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/transcribe` | multipart `audio` file + `language` (`auto`/`hi`/`mr`) → transcript + detected language |
| POST | `/api/structure` | `{transcript, language}` → `{steps: [{step_number, text, is_safety_warning, icon}]}` |
| POST | `/api/tts` | `{text, language}` → `{audio_url}` |
| GET | `/api/audio/{key}` | Serves the cached MP3 |
| GET | `/preview` | Demo web page |

## How to run it

### Local (Python)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

`ffmpeg` must be on PATH (librosa needs it to decode mp3).

Then open:
- Preview UI — http://localhost:8000/preview
- Swagger docs — http://localhost:8000/docs

First request downloads the Whisper checkpoints from Hugging Face (a few GB), so
it is slow; later requests use the cached models.

### Docker

```bash
cd backend
docker build -t voice-to-sop .
docker run -p 8000:8000 --env-file .env voice-to-sop
```

### Deploy

- **Render** — `render.yaml` at repo root; docker runtime, rootDir `backend`,
  health check `/api/health`. `V2S_LLM_API_KEY` is marked `sync: false`, so it
  must be set manually in the Render dashboard.
- **Railway** — `backend/railway.json`; Dockerfile builder, health check
  `/api/health` with a 300s timeout for the slow first boot.

## What API key it is using

Only **one** external API key is needed: the **LLM key for stage 2**.

- Variable: `V2S_LLM_API_KEY`
- Provider in use: **Groq** (`V2S_LLM_BASE_URL=https://api.groq.com/openai/v1`),
  model `gpt-oss-120b` locally / `llama-3.3-70b-versatile` in `render.yaml`
- Stored in `backend/.env`, which is **gitignored** (a real Groq key `gsk_...` is
  currently sitting in that file locally — it should be rotated if it has ever
  been shared or pasted anywhere)
- The endpoint is plain OpenAI-compatible chat completions, so Groq can be
  swapped for OpenAI, Together, or a local Ollama (`http://localhost:11434/v1`,
  key value ignored) just by changing the three `V2S_LLM_*` variables.

No key is required for ASR (Hugging Face public models) or TTS (edge-tts uses
Microsoft's free Edge endpoint).

All settings use the `V2S_` env prefix — e.g. `V2S_ASR_DEVICE=cuda`,
`V2S_TTS_VOICE_HI=...`, `V2S_LLM_TIMEOUT_SECONDS=120`.
