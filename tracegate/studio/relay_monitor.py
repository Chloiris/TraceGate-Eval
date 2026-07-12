from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from tracegate.github import GitHubAPIError

from .github_sync import sync_repository_pull_requests
from .models import AppSettings, Repository, WebhookDelivery
from .run_manager import RunManager


MAX_EVENT_CHARS = 16 * 1024
MAX_LOCAL_DEDUP = 1024
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class RelayMonitorError(RuntimeError):
    """Raised when a configured Relay stream cannot be consumed safely."""


class RelayEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_id: str = Field(min_length=1, max_length=128)
    event: Literal["pull_request", "pull_request_review", "check_run", "check_suite"]
    action: str | None = Field(default=None, max_length=128)
    repository: str
    pull_request_number: int | None = Field(default=None, ge=1)
    head_sha: str | None = Field(default=None, min_length=7, max_length=64)
    sender: str | None = Field(default=None, max_length=255)
    received_at: datetime

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        if not _REPOSITORY.fullmatch(value):
            raise ValueError("relay repository must use owner/name")
        return value


@dataclass(frozen=True)
class RelayMonitorSnapshot:
    running: bool
    connected: bool
    reconnect_count: int
    last_connected_at: datetime | None
    last_event_at: datetime | None
    last_repository: str | None
    last_error: str | None


class RelayMonitor:
    """Authenticated repository-scoped SSE consumer for the optional Relay."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        run_manager: RunManager,
    ) -> None:
        self.session_factory = session_factory
        self.run_manager = run_manager
        self._stop = asyncio.Event()
        self._wake = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._connected = False
        self._reconnect_count = 0
        self._last_connected_at: datetime | None = None
        self._last_event_at: datetime | None = None
        self._last_repository: str | None = None
        self._last_error: str | None = None
        self._recent_ids: deque[str] = deque(maxlen=MAX_LOCAL_DEDUP)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="tracegate-webhook-relay-monitor")

    def wake(self) -> None:
        self._wake.set()

    async def shutdown(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._task is not None:
            await asyncio.gather(self._task, return_exceptions=True)
        self._task = None
        self._connected = False

    def snapshot(self) -> RelayMonitorSnapshot:
        return RelayMonitorSnapshot(
            running=self._task is not None and not self._task.done(),
            connected=self._connected,
            reconnect_count=self._reconnect_count,
            last_connected_at=self._last_connected_at,
            last_event_at=self._last_event_at,
            last_repository=self._last_repository,
            last_error=self._last_error,
        )

    def _configuration(self) -> tuple[str, str] | None:
        with self.session_factory() as session:
            settings = session.get(AppSettings, 1)
            if settings is None or not settings.webhook_relay_url:
                return None
        token = os.environ.get("TRACEGATE_RELAY_DEVICE_TOKEN")
        if not token:
            return None
        return settings.webhook_relay_url, token

    async def _run(self) -> None:
        backoff_seconds = 1
        while not self._stop.is_set():
            configuration = self._configuration()
            if configuration is None:
                self._connected = False
                self._last_error = None
                await self._wait(30)
                continue
            try:
                await self._consume(*configuration)
                backoff_seconds = 1
            except asyncio.CancelledError:
                raise
            except (httpx.HTTPError, RelayMonitorError, GitHubAPIError, SQLAlchemyError, ValueError) as exc:
                self._connected = False
                self._reconnect_count += 1
                self._last_error = f"{type(exc).__name__}: {exc}"
                await self._wait(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 30)

    async def _wait(self, seconds: int) -> None:
        self._wake.clear()
        try:
            await asyncio.wait_for(self._wake.wait(), timeout=seconds)
        except TimeoutError:
            return None

    async def _consume(self, base_url: str, token: str) -> None:
        timeout = httpx.Timeout(connect=10, read=35, write=10, pool=10)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            async with client.stream(
                "GET",
                f"{base_url}/v1/events",
                headers={"Authorization": f"Bearer {token}", "Accept": "text/event-stream"},
            ) as response:
                if response.status_code != 200:
                    raise RelayMonitorError(f"Relay SSE returned HTTP {response.status_code}")
                content_type = response.headers.get("content-type", "")
                if "text/event-stream" not in content_type:
                    raise RelayMonitorError("Relay response is not an event stream")
                self._connected = True
                self._last_connected_at = datetime.now(timezone.utc)
                self._last_error = None
                async for line in response.aiter_lines():
                    if self._stop.is_set() or self._wake.is_set():
                        return
                    if not line.startswith("data: "):
                        continue
                    encoded = line[6:]
                    if len(encoded) > MAX_EVENT_CHARS:
                        raise RelayMonitorError("Relay event exceeded the local size limit")
                    try:
                        event = RelayEvent.model_validate_json(encoded)
                    except ValueError as exc:
                        raise RelayMonitorError("Relay event failed schema validation") from exc
                    await self._handle_event(event, encoded)
        self._connected = False
        if not self._stop.is_set() and not self._wake.is_set():
            raise RelayMonitorError("Relay SSE stream ended unexpectedly")

    async def _handle_event(self, event: RelayEvent, encoded: str) -> None:
        if event.delivery_id in self._recent_ids:
            return
        payload_hash = hashlib.sha256(encoded.encode()).hexdigest()
        local_delivery_id = "relay-" + hashlib.sha256(event.delivery_id.encode()).hexdigest()
        with self.session_factory() as session:
            existing = session.scalar(
                select(WebhookDelivery).where(WebhookDelivery.delivery_id == local_delivery_id)
            )
            if existing is not None:
                if existing.payload_hash != payload_hash:
                    raise RelayMonitorError("Relay delivery ID was replayed with different content")
                self._recent_ids.append(event.delivery_id)
                return
            record = WebhookDelivery(
                delivery_id=local_delivery_id,
                event=event.event,
                payload_hash=payload_hash,
                status="received",
                repository_full_name=event.repository,
                pull_request_number=event.pull_request_number,
            )
            session.add(record)
            session.commit()
            repository = session.scalar(
                select(Repository).where(Repository.full_name == event.repository)
            )
            if repository is None:
                record.status = "ignored_repository"
                record.processed_at = datetime.now(timezone.utc)
                session.commit()
            else:
                try:
                    await sync_repository_pull_requests(session, repository)
                except GitHubAPIError as exc:
                    record.status = "failed"
                    record.error_message = f"{type(exc).__name__}: {exc}"
                    record.processed_at = datetime.now(timezone.utc)
                    session.commit()
                    raise
                record.status = "processed"
                record.processed_at = datetime.now(timezone.utc)
                session.commit()
                automatic = self.run_manager.enqueue_automatic(repository.id)
                if automatic.skipped_reason:
                    self._last_error = automatic.skipped_reason
        self._recent_ids.append(event.delivery_id)
        self._last_event_at = datetime.now(timezone.utc)
        self._last_repository = event.repository


def parse_relay_event(encoded: str) -> RelayEvent:
    """Testable strict parser used by relay fixtures and boundary tests."""
    if len(encoded) > MAX_EVENT_CHARS:
        raise RelayMonitorError("Relay event exceeded the local size limit")
    try:
        return RelayEvent.model_validate(json.loads(encoded))
    except (json.JSONDecodeError, ValueError) as exc:
        raise RelayMonitorError("Relay event failed schema validation") from exc
