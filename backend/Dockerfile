FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
# Vite inlines VITE_* vars into the bundle at build time, not runtime - both Render and Railway
# expose configured env vars as Docker build ARGs automatically when the Dockerfile declares a
# matching ARG, which is how these reach `npm run build` below. The anon key is public-by-design
# (meant to ship to the browser), so baking it into the image is not a secret-handling concern.
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

# ffmpeg: librosa needs it to decode mp3 (uploaded audio, edge-tts output).
# libsndfile1: required by soundfile.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# hf-xet (huggingface_hub's chunked transfer backend) hangs indefinitely on
# some networks - must be set before the download step below, not after.
ENV HF_HUB_DISABLE_XET=1

# Bake model weights into the image so cold starts don't re-download from
# Hugging Face on every deploy/restart (Render's disk is ephemeral).
RUN python -c "\
from transformers import pipeline, WhisperProcessor, WhisperForConditionalGeneration; \
pipeline('automatic-speech-recognition', model='vasista22/whisper-hindi-medium'); \
pipeline('automatic-speech-recognition', model='steja/whisper-small-marathi'); \
WhisperProcessor.from_pretrained('openai/whisper-tiny'); \
WhisperForConditionalGeneration.from_pretrained('openai/whisper-tiny'); \
from transformers import GenerationConfig; \
GenerationConfig.from_pretrained('openai/whisper-medium'); \
GenerationConfig.from_pretrained('openai/whisper-small'); \
"

EXPOSE 8000

# Schema is Alembic-managed now (db.init() no longer creates tables on boot - see
# app/main.py's lifespan), so a migration run must happen before the app starts serving.
# Render injects $PORT at runtime; shell form so both variables expand.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
