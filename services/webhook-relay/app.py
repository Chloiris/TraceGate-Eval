from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_DELIVERIES = 10_000
MAX_QUEUE_EVENTS = 128
PAIRING_TTL = timedelta(minutes=10)
SUPPORTED_EVENTS = frozenset({"pull_request", "pull_request_review", "check_run", "check_suite"})
_DELIVERY_ID = re.compile(r"^[A-Za-z0-9-]{1,128}$")
_DEVICE_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class RelayError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class PairingCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repositories: list[str] = Field(min_length=1, max_length=100)

    @field_validator("repositories")
    @classmethod
    def validate_repositories(cls, value: list[str]) -> list[str]:
        normalized = sorted(set(value))
        if len(normalized) != len(value) or any(not _REPOSITORY.fullmatch(item) for item in normalized):
            raise ValueError("repositories must be unique owner/name values")
        return normalized


class PairingCodeResponse(BaseModel):
    pairing_code: str
    expires_at: datetime


class PairDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pairing_code: str = Field(min_length=20, max_length=128)
    device_id: str = Field(min_length=1, max_length=128)

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, value: str) -> str:
        if not _DEVICE_ID.fullmatch(value):
            raise ValueError("device_id is invalid")
        return value


class PairDeviceResponse(BaseModel):
    device_token: str
    repositories: list[str]


class WebhookResponse(BaseModel):
    accepted: bool
    duplicate: bool
    delivered_devices: int


@dataclass
class PendingPairing:
    repositories: frozenset[str]
    expires_at: datetime


@dataclass
class PairedDevice:
    device_id: str
    repositories: frozenset[str]
    queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=MAX_QUEUE_EVENTS)
    )


class RelayState:
    def __init__(self, *, admin_token: str, github_secret: str) -> None:
        if len(admin_token) < 32 or len(github_secret) < 32:
            raise ValueError("relay admin token and GitHub secret must each contain at least 32 characters")
        self.admin_token = admin_token
        self.github_secret = github_secret
        self.pending_pairings: dict[str, PendingPairing] = {}
        self.devices_by_token_hash: dict[str, PairedDevice] = {}
        self.deliveries: OrderedDict[str, str] = OrderedDict()

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def authenticate_admin(self, authorization: str | None) -> None:
        token = _bearer_token(authorization)
        if token is None or not hmac.compare_digest(token, self.admin_token):
            raise RelayError(401, "invalid_admin_token", "Relay administrator authentication failed.")

    def authenticate_device(self, authorization: str | None) -> PairedDevice:
        token = _bearer_token(authorization)
        device = self.devices_by_token_hash.get(self.token_hash(token)) if token else None
        if device is None:
            raise RelayError(401, "invalid_device_token", "Relay device authentication failed.")
        return device

    def create_pairing(self, repositories: list[str]) -> tuple[str, datetime]:
        self._purge_pairings()
        code = secrets.token_urlsafe(32)
        expires_at = _now() + PAIRING_TTL
        self.pending_pairings[self.token_hash(code)] = PendingPairing(
            repositories=frozenset(repositories),
            expires_at=expires_at,
        )
        return code, expires_at

    def pair(self, code: str, device_id: str) -> tuple[str, PairedDevice]:
        self._purge_pairings()
        pending = self.pending_pairings.pop(self.token_hash(code), None)
        if pending is None:
            raise RelayError(401, "invalid_pairing_code", "Pairing code is invalid, expired, or already used.")
        token = secrets.token_urlsafe(48)
        device = PairedDevice(device_id=device_id, repositories=pending.repositories)
        self.devices_by_token_hash[self.token_hash(token)] = device
        return token, device

    def record_delivery(self, delivery_id: str, payload_hash: str) -> bool:
        existing = self.deliveries.get(delivery_id)
        if existing is not None:
            if not hmac.compare_digest(existing, payload_hash):
                raise RelayError(409, "delivery_mismatch", "Delivery ID was replayed with different content.")
            return True
        self.deliveries[delivery_id] = payload_hash
        while len(self.deliveries) > MAX_DELIVERIES:
            self.deliveries.popitem(last=False)
        return False

    def broadcast(self, repository: str, event: dict[str, Any]) -> int:
        delivered = 0
        for device in self.devices_by_token_hash.values():
            if repository not in device.repositories:
                continue
            if device.queue.full():
                device.queue.get_nowait()
            device.queue.put_nowait(event)
            delivered += 1
        return delivered

    def _purge_pairings(self) -> None:
        now = _now()
        expired = [key for key, value in self.pending_pairings.items() if value.expires_at <= now]
        for key in expired:
            self.pending_pairings.pop(key, None)


def create_app(*, admin_token: str | None = None, github_secret: str | None = None) -> FastAPI:
    resolved_admin_token = admin_token or os.environ.get("TRACEGATE_RELAY_ADMIN_TOKEN", "")
    resolved_github_secret = github_secret or os.environ.get("TRACEGATE_RELAY_GITHUB_SECRET", "")
    state = RelayState(admin_token=resolved_admin_token, github_secret=resolved_github_secret)
    app = FastAPI(title="TraceGate Webhook Relay", version="0.4.0")
    app.state.relay = state

    @app.exception_handler(RelayError)
    async def relay_error_handler(_request: Request, error: RelayError):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            {"error": {"code": error.code, "message": str(error)}},
            status_code=error.status_code,
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/pairing-codes", response_model=PairingCodeResponse)
    async def create_pairing_code(
        payload: PairingCodeRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> PairingCodeResponse:
        state.authenticate_admin(authorization)
        code, expires_at = state.create_pairing(payload.repositories)
        return PairingCodeResponse(pairing_code=code, expires_at=expires_at)

    @app.post("/v1/devices/pair", response_model=PairDeviceResponse)
    async def pair_device(payload: PairDeviceRequest) -> PairDeviceResponse:
        token, device = state.pair(payload.pairing_code, payload.device_id)
        return PairDeviceResponse(device_token=token, repositories=sorted(device.repositories))

    @app.get("/v1/events")
    async def events(authorization: Annotated[str | None, Header()] = None) -> StreamingResponse:
        device = state.authenticate_device(authorization)

        async def stream():
            yield ": tracegate-relay-connected\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(device.queue.get(), timeout=20)
                    encoded = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
                    yield f"event: github\ndata: {encoded}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @app.post("/v1/github", response_model=WebhookResponse)
    async def github_webhook(
        request: Request,
        x_github_delivery: Annotated[str | None, Header()] = None,
        x_github_event: Annotated[str | None, Header()] = None,
        x_hub_signature_256: Annotated[str | None, Header()] = None,
    ) -> WebhookResponse:
        body = await _bounded_body(request)
        _validate_github_signature(state.github_secret, body, x_hub_signature_256)
        if x_github_delivery is None or not _DELIVERY_ID.fullmatch(x_github_delivery):
            raise RelayError(422, "invalid_delivery_id", "X-GitHub-Delivery is required and invalid.")
        if x_github_event not in SUPPORTED_EVENTS:
            raise RelayError(422, "unsupported_event", "GitHub event type is not supported.")
        payload_hash = hashlib.sha256(body).hexdigest()
        try:
            payload = json.loads(body)
            repository = payload["repository"]["full_name"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RelayError(422, "invalid_payload", "GitHub payload is invalid.") from exc
        if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
            raise RelayError(422, "invalid_repository", "GitHub repository identity is invalid.")
        duplicate = state.record_delivery(x_github_delivery, payload_hash)
        if duplicate:
            return WebhookResponse(accepted=True, duplicate=True, delivered_devices=0)
        event = _public_event(x_github_delivery, x_github_event, repository, payload)
        return WebhookResponse(
            accepted=True,
            duplicate=False,
            delivered_devices=state.broadcast(repository, event),
        )

    return app


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _bearer_token(authorization: str | None) -> str | None:
    if authorization is None or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    return token if token and len(token) <= 512 else None


async def _bounded_body(request: Request) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            parsed = int(content_length)
        except ValueError as exc:
            raise RelayError(400, "invalid_content_length", "Content-Length is invalid.") from exc
        if parsed < 0:
            raise RelayError(400, "invalid_content_length", "Content-Length is invalid.")
        if parsed > MAX_BODY_BYTES:
            raise RelayError(413, "payload_too_large", "Webhook payload exceeded 2 MiB.")
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise RelayError(413, "payload_too_large", "Webhook payload exceeded 2 MiB.")
    return body


def _validate_github_signature(secret: str, body: bytes, signature: str | None) -> None:
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if signature is None or not hmac.compare_digest(signature, expected):
        raise RelayError(401, "invalid_signature", "GitHub webhook signature is invalid.")


def _public_event(delivery_id: str, event_name: str, repository: str, payload: dict[str, Any]) -> dict[str, Any]:
    pull_request = payload.get("pull_request") if isinstance(payload.get("pull_request"), dict) else {}
    head = pull_request.get("head") if isinstance(pull_request.get("head"), dict) else {}
    sender = payload.get("sender") if isinstance(payload.get("sender"), dict) else {}
    return {
        "delivery_id": delivery_id,
        "event": event_name,
        "action": payload.get("action") if isinstance(payload.get("action"), str) else None,
        "repository": repository,
        "pull_request_number": pull_request.get("number") if isinstance(pull_request.get("number"), int) else None,
        "head_sha": head.get("sha") if isinstance(head.get("sha"), str) else None,
        "sender": sender.get("login") if isinstance(sender.get("login"), str) else None,
        "received_at": _now().isoformat(),
    }
