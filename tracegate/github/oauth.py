from __future__ import annotations

import inspect
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class GitHubOAuthError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class DeviceAuthorizationPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_code: str
    verification_uri: str
    expires_at: datetime
    interval_seconds: int


@dataclass
class DeviceAuthorizationSession:
    device_code: SecretStr
    public: DeviceAuthorizationPublic
    next_poll_monotonic: float


class DeviceCodeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    device_code: SecretStr
    user_code: str = Field(min_length=1, max_length=128)
    verification_uri: str
    expires_in: int = Field(gt=0, le=3600)
    interval: int = Field(default=5, ge=1, le=60)

    @field_validator("verification_uri")
    @classmethod
    def github_verification_uri(cls, value: str) -> str:
        if value != "https://github.com/login/device":
            raise ValueError("GitHub returned an unexpected verification URI")
        return value


TokenSink = Callable[[SecretStr], None | Awaitable[None]]


class GitHubDeviceFlow:
    """GitHub OAuth device flow that sends tokens only to a secure sink."""

    def __init__(
        self,
        client_id: str,
        token_sink: TokenSink,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        if not client_id or len(client_id) > 255 or any(character.isspace() for character in client_id):
            raise ValueError("GitHub OAuth client ID is invalid")
        self.client_id = client_id
        self.token_sink = token_sink
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            base_url="https://github.com",
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            headers={"Accept": "application/json", "User-Agent": "TraceGate-Studio/0.1"},
        )

    async def begin(self, scope: str = "read:user repo") -> DeviceAuthorizationSession:
        response = await self._post(
            "/login/device/code",
            {"client_id": self.client_id, "scope": scope},
        )
        try:
            payload = DeviceCodeResponse.model_validate(response)
        except ValueError as exc:
            raise GitHubOAuthError("invalid_device_response", "GitHub device response is invalid") from exc
        now = datetime.now(timezone.utc)
        public = DeviceAuthorizationPublic(
            user_code=payload.user_code,
            verification_uri=payload.verification_uri,
            expires_at=now + timedelta(seconds=payload.expires_in),
            interval_seconds=payload.interval,
        )
        return DeviceAuthorizationSession(
            device_code=payload.device_code,
            public=public,
            next_poll_monotonic=time.monotonic(),
        )

    async def poll(self, session: DeviceAuthorizationSession) -> str:
        if datetime.now(timezone.utc) >= session.public.expires_at:
            raise GitHubOAuthError("expired_token", "GitHub device authorization expired")
        now = time.monotonic()
        if now < session.next_poll_monotonic:
            raise GitHubOAuthError("poll_interval", "GitHub device authorization was polled too quickly")
        response = await self._post(
            "/login/oauth/access_token",
            {
                "client_id": self.client_id,
                "device_code": session.device_code.get_secret_value(),
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        error = response.get("error")
        if error == "authorization_pending":
            session.next_poll_monotonic = now + session.public.interval_seconds
            return "pending"
        if error == "slow_down":
            session.public.interval_seconds += 5
            session.next_poll_monotonic = now + session.public.interval_seconds
            return "pending"
        if error in {"expired_token", "access_denied"}:
            raise GitHubOAuthError(str(error), f"GitHub device authorization failed: {error}")
        token = response.get("access_token")
        if not isinstance(token, str) or len(token) < 20:
            raise GitHubOAuthError("invalid_token_response", "GitHub OAuth token response is invalid")
        outcome = self.token_sink(SecretStr(token))
        if inspect.isawaitable(outcome):
            await outcome
        return "authorized"

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _post(self, path: str, data: dict[str, str]) -> dict[str, Any]:
        try:
            response = await self.client.post(path, data=data)
        except httpx.HTTPError as exc:
            raise GitHubOAuthError("network_error", f"GitHub OAuth request failed: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise GitHubOAuthError("http_error", f"GitHub OAuth returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GitHubOAuthError("invalid_json", "GitHub OAuth returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise GitHubOAuthError("invalid_json", "GitHub OAuth response is not an object")
        return payload
