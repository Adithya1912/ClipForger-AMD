from __future__ import annotations

import json
import re
from typing import Any

import requests

from .config import settings


class CaptionLLMClient:
    fireworks_endpoint = "https://api.fireworks.ai/inference/v1/chat/completions"
    groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
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
        if provider in {"gemma", "fireworks_gemma"}:
            return ["fireworks_gemma"] if settings.fireworks_api_key and settings.fireworks_gemma_model else []
        if provider == "fireworks":
            return ["fireworks"] if settings.fireworks_api_key else []
        if provider == "groq":
            return ["groq"] if settings.groq_api_key else []

        order: list[str] = []
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
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            return json.loads(match.group(0)) if match else fallback


caption_llm = CaptionLLMClient()
