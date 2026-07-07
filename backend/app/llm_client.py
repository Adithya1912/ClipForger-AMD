from __future__ import annotations

import json
import re
from typing import Any

import requests

from .config import settings


class CaptionLLMClient:
    fireworks_endpoint = "https://api.fireworks.ai/inference/v1/chat/completions"
    groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
    openrouter_endpoint = "https://openrouter.ai/api/v1/chat/completions"
    google_endpoint = "https://generativelanguage.googleapis.com/v1beta/models"
    nvidia_endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
    last_provider_errors: list[str] = []

    def complete_json(self, messages: list[dict[str, str]], fallback: dict[str, Any]) -> tuple[dict[str, Any], str]:
        providers = self._provider_order()
        errors: list[str] = self._configuration_notes()
        self.last_provider_errors = []
        strict_provider = settings.llm_provider.lower() not in {"", "auto"}

        for provider in providers:
            try:
                data = self._complete_with_provider(provider, messages)
                self.last_provider_errors = errors
                return self._parse_json(data, fallback), provider
            except Exception as exc:
                errors.append(f"{provider}: {exc}")

        if strict_provider:
            self.last_provider_errors = errors
            detail = " | ".join(errors) if errors else f"{settings.llm_provider} is not configured"
            raise RuntimeError(f"Required LLM provider failed: {detail}")

        if errors:
            fallback["_provider_error"] = " | ".join(errors)
        self.last_provider_errors = errors
        return fallback, "local_fallback"

    def _provider_order(self) -> list[str]:
        provider = settings.llm_provider.lower()
        if provider == "nvidia":
            return ["nvidia"] if settings.nvidia_api_key else []
        if provider == "google":
            return ["google"] if settings.google_api_key else []
        if provider in {"gemma", "google_gemma"}:
            if settings.google_api_key:
                return ["google"]
            if settings.fireworks_api_key and settings.fireworks_gemma_model:
                return ["fireworks_gemma"]
            return []
        if provider == "openrouter":
            return ["openrouter"] if settings.openrouter_api_key else []
        if provider in {"fireworks_gemma"}:
            return ["fireworks_gemma"] if settings.fireworks_api_key and settings.fireworks_gemma_model else []
        if provider == "fireworks":
            return ["fireworks"] if settings.fireworks_api_key else []
        if provider == "groq":
            return ["groq"] if settings.groq_api_key else []

        order: list[str] = []
        if settings.openrouter_api_key:
            order.append("openrouter")
        if settings.nvidia_api_key:
            order.append("nvidia")
        if settings.google_api_key:
            order.append("google")
        if settings.fireworks_api_key and settings.fireworks_gemma_model:
            order.append("fireworks_gemma")
        if settings.fireworks_api_key:
            order.append("fireworks")
        if settings.groq_api_key:
            order.append("groq")
        return order

    def _configuration_notes(self) -> list[str]:
        provider = settings.llm_provider.lower()
        notes: list[str] = []
        if provider in {"auto", "gemma", "nvidia"} and not settings.nvidia_api_key:
            notes.append("nvidia skipped: NVIDIA_API_KEY is not configured")
        if provider in {"auto", "gemma", "google", "google_gemma"} and not settings.google_api_key:
            notes.append("google skipped: GOOGLE_API_KEY is not configured")
        if provider in {"auto", "gemma", "openrouter", "openrouter_gemma"} and not settings.openrouter_api_key:
            notes.append("openrouter skipped: OPENROUTER_API_KEY is not configured")
        if provider in {"auto", "gemma", "fireworks_gemma"}:
            if settings.fireworks_api_key and not settings.fireworks_gemma_model:
                notes.append("fireworks_gemma skipped: FIREWORKS_GEMMA_MODEL is not configured")
            elif settings.fireworks_gemma_model and not settings.fireworks_api_key:
                notes.append("fireworks_gemma skipped: FIREWORKS_API_KEY is not configured")
        if provider in {"auto", "fireworks"} and not settings.fireworks_api_key:
            notes.append("fireworks skipped: FIREWORKS_API_KEY is not configured")
        if provider in {"auto", "groq"} and not settings.groq_api_key:
            notes.append("groq skipped: GROQ_API_KEY is not configured")
        return notes

    def _complete_with_provider(self, provider: str, messages: list[dict[str, str]]) -> str:
        if provider == "nvidia":
            response = requests.post(
                self.nvidia_endpoint,
                headers={
                    "Authorization": f"Bearer {settings.nvidia_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.nvidia_model,
                    "messages": messages,
                    "temperature": 0.35,
                    "max_tokens": 1024,
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        if provider == "google":
            is_gemini = "gemini" in settings.google_model.lower()
            is_gemma = "gemma" in settings.google_model.lower()

            if is_gemma:
                system_text = ""
                user_text = ""
                for msg in messages:
                    if msg["role"] == "system":
                        system_text = msg["content"]
                    elif msg["role"] == "user" and not user_text:
                        user_text = msg["content"]
                combined = f"{system_text}\n\n{user_text}\n\nReturn ONLY valid JSON with keys: styled_caption, summary, tone_notes, confidence. Start your response with: {{\"styled_caption\": \""
                body = {
                    "contents": [{"role": "user", "parts": [{"text": combined}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1024,
                    },
                }
            else:
                system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
                user_parts = [{"text": m["content"]} for m in messages if m["role"] == "user"]
                contents = [{"role": "user", "parts": user_parts}] if user_parts else []
                body: dict[str, Any] = {
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.35,
                        "maxOutputTokens": 1024,
                    },
                }
                if is_gemini:
                    body["generationConfig"]["responseMimeType"] = "application/json"
                if system_msg:
                    body["systemInstruction"] = {"parts": [{"text": system_msg}]}

            response = requests.post(
                f"{self.google_endpoint}/{settings.google_model}:generateContent?key={settings.google_api_key}",
                json=body,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError(f"Google returned no candidates: {data}")
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not text:
                raise RuntimeError(f"Google returned empty text: {data}")
            if is_gemma:
                text = '{"styled_caption": "' + text
            return text

        if provider == "openrouter":
            for attempt in range(2):
                msgs = messages[:]
                for msg in msgs:
                    if msg["role"] == "system":
                        append = " Respond with ONLY valid JSON." if attempt == 0 else " Respond with ONLY JSON. Keep it brief."
                        msg["content"] = msg["content"].rstrip() + append
                if attempt == 1:
                    msgs = [m for m in msgs if not (m["role"] == "assistant" and any(
                        kw in m["content"] for kw in ["Evidence", "Generate"]
                    ))]
                    msgs = msgs[-2:] if len(msgs) > 3 else msgs
                try:
                    response = requests.post(
                        self.openrouter_endpoint,
                        headers={
                            "Authorization": f"Bearer {settings.openrouter_api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://github.com/clipforger-amd",
                            "X-Title": "ClipForger-AMD",
                        },
                        json={
                            "model": settings.openrouter_model,
                            "messages": msgs,
                            "temperature": 0.35 if attempt == 0 else 0.4,
                            "max_tokens": 1024,
                        },
                        timeout=120,
                    )
                    if response.status_code == 429 and attempt == 0:
                        continue
                    response.raise_for_status()
                    return response.json()["choices"][0]["message"]["content"]
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 429 and attempt == 0:
                        continue
                    raise
            raise RuntimeError("OpenRouter failed after 2 attempts")

        if provider in {"fireworks", "fireworks_gemma"}:
            model = settings.fireworks_gemma_model if provider == "fireworks_gemma" else settings.fireworks_model
            response = requests.post(
                self.fireworks_endpoint,
                headers={
                    "Authorization": f"Bearer {settings.fireworks_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.55,
                    "response_format": {"type": "json_object"},
                },
                timeout=60,
            )
        elif provider == "groq":
            response = requests.post(
                self.groq_endpoint,
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.groq_model,
                    "messages": messages,
                    "temperature": 0.55,
                    "response_format": {"type": "json_object"},
                },
                timeout=60,
            )
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_json(content: str, fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list) and len(parsed) > 0:
                parsed = parsed[0]
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        brace_match = re.search(r"\{.*\}", content, re.DOTALL)
        if brace_match:
            try:
                parsed = json.loads(brace_match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
        key_vals: dict[str, Any] = {}
        for key in ("styled_caption", "summary", "caption", "tone_notes", "confidence"):
            pattern = re.compile(
                rf'(?:^|\*|[`\'\"]?)\s*{key}\s*(?::|=)\s*[`\'\"]?(.*?)(?:["\']?\s*(?:\n|\*|$|,))',
                re.IGNORECASE | re.DOTALL,
            )
            match = pattern.search(content)
            if match:
                val = match.group(1).strip().rstrip(",").strip()
                if val:
                    if key == "confidence":
                        try:
                            key_vals[key] = float(val)
                        except ValueError:
                            key_vals[key] = 0.75
                    else:
                        key_vals[key] = val
        if "styled_caption" in key_vals or "summary" in key_vals:
            return key_vals
        return fallback


caption_llm = CaptionLLMClient()
