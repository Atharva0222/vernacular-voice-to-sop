import logging
import re
import threading

import librosa
import numpy as np
import torch
from transformers import GenerationConfig, WhisperForConditionalGeneration, WhisperProcessor, pipeline

from app.config import settings

log = logging.getLogger(__name__)

_lock = threading.Lock()
_asr_pipelines: dict[str, object] = {}
_asr_generation_configs: dict[str, GenerationConfig] = {}
_lang_id_processor: WhisperProcessor | None = None
_lang_id_model: WhisperForConditionalGeneration | None = None

_MODEL_BY_LANG = {
    "hi": settings.asr_model_hi,
    "mr": settings.asr_model_mr,
}

# Full language names Whisper's tokenizer expects for generate_kwargs.
_WHISPER_LANG_NAME = {
    "hi": "hindi",
    "mr": "marathi",
}

# These fine-tunes predate transformers' language=/task= generate() kwargs and ship a
# stale generation_config (suppress_tokens=[], forced_decoder_ids=null) that crashes on
# newer transformers. Same architecture as the base OpenAI checkpoint they were fine-tuned
# from, so swapping in the base model's generation_config fixes it without touching weights.
# https://github.com/huggingface/transformers/issues/25084#issuecomment-1664398224
_BASE_MODEL_FOR_GENERATION_CONFIG = {
    "hi": "openai/whisper-medium",
    "mr": "openai/whisper-small",
}

_LANG_TOKEN_RE = re.compile(r"<\|([a-z]{2})\|>")

_SAMPLE_RATE = 16000
# These fine-tunes were trained on short utterance-level clips, not long-form
# audio with timestamp tokens, so both the pipeline's chunk_length_s stitching
# and native long-form generation silently drop/garble the middle of anything
# over ~30s. Fixed-duration windows are just as unreliable since they can land
# mid-word. Splitting on actual silence gaps between sentences (never mid-word)
# and transcribing each group separately avoids all of that.
#
# 4s, not larger: swept over {4,5,6,8,10,15,25}s against clips with known text, the
# models stop generating after the first sentence of any window that holds more than
# one. A 68s/15-sentence clip recovers 15/15 at 4s and 5s, 14/15 at 6s, 10/15 at 8s,
# 4/15 at 25s; a 10s worker complaint needs 4s to keep all three of its sentences.
_WINDOW_SECONDS = 4.0
_SILENCE_TOP_DB = 30


def _resolve_device() -> str:
    if settings.asr_device != "auto":
        return settings.asr_device
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_audio(path: str) -> np.ndarray:
    audio, _ = librosa.load(path, sr=16000, mono=True)
    return audio


def _split_on_silence(audio: np.ndarray) -> list[np.ndarray]:
    """Group non-silent intervals into windows up to _WINDOW_SECONDS, splitting
    only at silence gaps so a boundary never lands mid-word."""
    intervals = librosa.effects.split(audio, top_db=_SILENCE_TOP_DB)
    if len(intervals) == 0:
        return [audio]

    windows = []
    cur_start, cur_end = intervals[0]
    for start, end in intervals[1:]:
        if (end - cur_start) / _SAMPLE_RATE > _WINDOW_SECONDS:
            windows.append(audio[cur_start:cur_end])
            cur_start = start
        cur_end = end
    windows.append(audio[cur_start:cur_end])
    return windows


# Hindi/Marathi speech runs well above 6 characters per second; anything far below
# that means the model stopped early, which is the silent failure this guard surfaces.
_MIN_CHARS_PER_SECOND = 3.0


def _warn_if_truncated(window: np.ndarray, text: str) -> None:
    """Log windows whose text is too short for their duration - the model stopped early."""
    seconds = len(window) / _SAMPLE_RATE
    if seconds >= 2.0 and len(text) / seconds < _MIN_CHARS_PER_SECOND:
        log.warning("possible ASR truncation: %.1fs window yielded %d characters: %r", seconds, len(text), text)


def _get_pipeline(language: str):
    with _lock:
        if language not in _asr_pipelines:
            model_id = _MODEL_BY_LANG[language]
            device = _resolve_device()
            asr_pipeline = pipeline(
                "automatic-speech-recognition",
                model=model_id,
                device=device,
            )
            gen_config = GenerationConfig.from_pretrained(_BASE_MODEL_FOR_GENERATION_CONFIG[language])
            asr_pipeline.model.generation_config = gen_config
            _asr_generation_configs[language] = gen_config
            _asr_pipelines[language] = asr_pipeline
        return _asr_pipelines[language]


def _get_lang_id_model():
    global _lang_id_processor, _lang_id_model
    with _lock:
        if _lang_id_model is None:
            _lang_id_processor = WhisperProcessor.from_pretrained(settings.asr_lang_id_model)
            _lang_id_model = WhisperForConditionalGeneration.from_pretrained(settings.asr_lang_id_model)
        return _lang_id_processor, _lang_id_model


def detect_language(audio: np.ndarray) -> str:
    """Lightweight language ID using whisper-tiny's built-in detection.

    Returns 'hi' or 'mr' if detected with confidence, otherwise falls back to 'hi'
    since we only have fine-tuned checkpoints for those two languages.
    """
    processor, model = _get_lang_id_model()
    input_features = processor(audio, sampling_rate=16000, return_tensors="pt").input_features
    predicted_ids = model.generate(input_features, language=None, max_new_tokens=1)
    decoded = processor.batch_decode(predicted_ids, skip_special_tokens=False)[0]
    match = _LANG_TOKEN_RE.search(decoded)
    detected = match.group(1) if match else None
    if detected in _MODEL_BY_LANG:
        return detected
    return "hi"


def transcribe(path: str, language_hint: str | None) -> tuple[str, str]:
    audio = load_audio(path)

    if language_hint in _MODEL_BY_LANG:
        language = language_hint
    else:
        language = detect_language(audio)

    asr = _get_pipeline(language)
    # generation_config must be passed explicitly here too - assigning it to
    # asr.model.generation_config alone isn't picked up by generate() reliably.
    generate_kwargs = {
        "language": _WHISPER_LANG_NAME[language],
        "task": "transcribe",
        "generation_config": _asr_generation_configs[language],
    }

    windows = _split_on_silence(audio)
    texts = []
    for window in windows:
        text = asr(window, generate_kwargs=generate_kwargs)["text"].strip()
        _warn_if_truncated(window, text)
        texts.append(text)
    transcript = " ".join(t for t in texts if t)
    return transcript, language
