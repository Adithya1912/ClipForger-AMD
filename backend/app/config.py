from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_DIR / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env", override=False)


def _duration_setting(name: str, default: float) -> float | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = float(raw)
    return None if value <= 0 else value


class Settings:
    app_name = "ClipForger"
    storage_dir = Path(os.getenv("STORAGE_DIR", "./data")).resolve()
    llm_provider = os.getenv("LLM_PROVIDER", "auto")
    fireworks_api_key = os.getenv("FIREWORKS_API_KEY", "")
    fireworks_model = os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/llama-v3p1-8b-instruct")
    fireworks_gemma_model = os.getenv("FIREWORKS_GEMMA_MODEL", "").strip()
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    groq_vision_model = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    groq_transcription_model = os.getenv("GROQ_TRANSCRIPTION_MODEL", "whisper-large-v3")
    transcription_language = os.getenv("TRANSCRIPTION_LANGUAGE", "en").strip()
    transcription_provider = os.getenv("TRANSCRIPTION_PROVIDER", "auto")
    visual_provider = os.getenv("VISUAL_PROVIDER", "auto")
    min_duration_seconds = _duration_setting("MIN_VIDEO_DURATION_SECONDS", 30)
    max_duration_seconds = _duration_setting("MAX_VIDEO_DURATION_SECONDS", 120)


settings = Settings()
