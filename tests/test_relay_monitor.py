from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from tracegate.studio.database import StudioDatabase
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import Repository, WebhookDelivery
from tracegate.studio.relay_monitor import (
    MAX_EVENT_CHARS,
    RelayMonitor,
    RelayMonitorError,
    parse_relay_event,
)


class FakeRunManager:
    def __init__(self) -> None:
        self.repositories: list[str] = []

    def enqueue_automatic(self, repository_id: str) -> SimpleNamespace:
        self.repositories.append(repository_id)
        return SimpleNamespace(skipped_reason=None)


def relay_event(**overrides: object) -> str:
    payload: dict[str, object] = {
        "delivery_id": "delivery-1",
        "event": "pull_request",
        "action": "synchronize",
        "repository": "acme/widget",
        "pull_request_number": 7,
        "head_sha": "a" * 40,
        "sender": "octocat",
        "received_at": "2026-07-10T10:00:00Z",
    }
    payload.update(overrides)
    return json.dumps(payload, separators=(",", ":"))


def test_relay_event_parser_is_strict_and_bounded() -> None:
    event = parse_relay_event(relay_event())
    assert event.repository == "acme/widget"
    assert event.pull_request_number == 7

    with pytest.raises(RelayMonitorError, match="schema validation"):
        parse_relay_event(relay_event(repository="owner/repository/extra"))
    with pytest.raises(RelayMonitorError, match="size limit"):
        parse_relay_event("x" * (MAX_EVENT_CHARS + 1))
    with pytest.raises(RelayMonitorError, match="schema validation"):
        parse_relay_event(relay_event(unexpected_secret="must be rejected"))


@pytest.mark.asyncio
async def test_relay_delivery_is_durable_scoped_and_deduplicated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'relay.db').as_posix()}"
    upgrade_database(database_url)
    database = StudioDatabase(database_url)
    with database.session_factory() as session:
        repository = Repository(owner="acme", name="widget", full_name="acme/widget")
        session.add(repository)
        session.commit()
        repository_id = repository.id

    synchronized: list[str] = []

    async def record_sync(_session, repository):  # type: ignore[no-untyped-def]
        synchronized.append(repository.id)
        return SimpleNamespace(status="success")

    monkeypatch.setattr("tracegate.studio.relay_monitor.sync_repository_pull_requests", record_sync)
    run_manager = FakeRunManager()
    monitor = RelayMonitor(database.session_factory, run_manager)  # type: ignore[arg-type]
    encoded = relay_event()

    try:
        await monitor._handle_event(parse_relay_event(encoded), encoded)
        await monitor._handle_event(parse_relay_event(encoded), encoded)

        assert synchronized == [repository_id]
        assert run_manager.repositories == [repository_id]
        with database.session_factory() as session:
            deliveries = list(session.scalars(select(WebhookDelivery)))
            assert len(deliveries) == 1
            assert deliveries[0].delivery_id.startswith("relay-")
            assert deliveries[0].delivery_id != "delivery-1"
            assert deliveries[0].status == "processed"
            assert deliveries[0].repository_full_name == "acme/widget"
            assert deliveries[0].processed_at is not None
    finally:
        database.dispose()


@pytest.mark.asyncio
async def test_relay_monitor_reconnects_after_a_stream_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'reconnect.db').as_posix()}"
    upgrade_database(database_url)
    database = StudioDatabase(database_url)
    monitor = RelayMonitor(database.session_factory, FakeRunManager())  # type: ignore[arg-type]
    attempts = 0
    waits: list[int] = []

    monkeypatch.setattr(monitor, "_configuration", lambda: ("https://relay.example.com", "device-token"))

    async def consume(_url: str, _token: str) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RelayMonitorError("stream disconnected")
        monitor._stop.set()

    async def wait(seconds: int) -> None:
        waits.append(seconds)

    monkeypatch.setattr(monitor, "_consume", consume)
    monkeypatch.setattr(monitor, "_wait", wait)
    try:
        await monitor._run()
        assert attempts == 2
        assert waits == [1]
        assert monitor.snapshot().reconnect_count == 1
        assert monitor.snapshot().last_error == "RelayMonitorError: stream disconnected"
    finally:
        database.dispose()
