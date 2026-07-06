from __future__ import annotations

import base64
from pathlib import Path

import requests

from .config import settings


NO_VISUAL_CONTEXT = "NO_VISUAL_CONTEXT_AVAILABLE"


def describe_frames(frame_paths: list[Path]) -> tuple[str, str]:
    provider = settings.visual_provider.lower()
    should_use_groq = provider in {"auto", "groq"} and bool(settings.groq_api_key)
    if not frame_paths:
        return f"{NO_VISUAL_CONTEXT}: No keyframes could be extracted.", "local_fallback"
    if should_use_groq:
        try:
            return _describe_with_groq(frame_paths), "groq"
        except Exception as exc:
            return f"{NO_VISUAL_CONTEXT}: Groq vision failed: {exc}", "local_fallback"
    return f"{NO_VISUAL_CONTEXT}: No vision provider is enabled.", "local_fallback"


def _describe_with_groq(frame_paths: list[Path]) -> str:
    content: list[dict] = [
        {
            "type": "text",
            "text": (
                "Describe the visible scene across these video keyframes for caption generation. "
                "Focus on people, setting, actions, objects, mood, and any visual joke. "
                "Do not mention that these are frames or images."
            ),
        }
    ]
    for path in frame_paths[:3]:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
            }
        )

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.groq_vision_model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.2,
            "max_tokens": 240,
        },
        timeout=120,
    )
    response.raise_for_status()
    text = str(response.json()["choices"][0]["message"]["content"]).strip()
    if not text:
        raise RuntimeError("Vision response did not include text.")
    return text
