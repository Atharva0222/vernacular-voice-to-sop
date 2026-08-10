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
COPY static_preview ./static_preview

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

# Render injects $PORT at runtime; shell form so the variable expands.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
