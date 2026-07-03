from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class DeepSeekClientError(RuntimeError):
    """Raised when DeepSeek cannot be called as a real semantic provider."""


@dataclass(frozen=True)
class DeepSeekSettings:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    timeout_seconds: int = 120

    @property
    def chat_completions_url(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"


@dataclass(frozen=True)
class DeepSeekResponse:
    model: str
    content: str
    raw_response: dict[str, Any]
    duration_seconds: float


def load_deepseek_settings_from_env(*, timeout_seconds: int = 120) -> DeepSeekSettings:
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("TRACEGATE_LLM_API_KEY")
    if not key:
        raise DeepSeekClientError(
            "Missing DeepSeek API key. Set DEEPSEEK_API_KEY or TRACEGATE_LLM_API_KEY; semantic mode has no fallback."
        )
    return DeepSeekSettings(
        api_key=key,
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        timeout_seconds=timeout_seconds,
    )


class DeepSeekClient:
    def __init__(self, settings: DeepSeekSettings) -> None:
        self.settings = settings
        self.call_count = 0

    @classmethod
    def from_env(cls, *, timeout_seconds: int = 120) -> "DeepSeekClient":
        return cls(load_deepseek_settings_from_env(timeout_seconds=timeout_seconds))

    def chat_json(self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 2000) -> DeepSeekResponse:
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.settings.chat_completions_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DeepSeekClientError(f"DeepSeek API HTTP {exc.code}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise DeepSeekClientError(f"DeepSeek API network error: {exc}") from exc

        self.call_count += 1
        try:
            raw_response = json.loads(body)
            content = raw_response["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise DeepSeekClientError("DeepSeek API returned an unexpected response shape") from exc
        return DeepSeekResponse(
            model=str(raw_response.get("model") or self.settings.model),
            content=str(content),
            raw_response=raw_response,
            duration_seconds=round(time.time() - started, 3),
        )
