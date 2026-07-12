from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from tracegate.studio.database import StudioDatabase
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import AppSettings, Repository
from tracegate.studio.monitor import RepositoryMonitor
from tracegate.github import GitHubAPIError


@pytest.mark.asyncio
async def test_monitor_polls_only_when_global_and_repository_flags_are_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'monitor.db').as_posix()}"
    upgrade_database(database_url)
    database = StudioDatabase(database_url)
    with database.session_factory() as session:
        repository = Repository(
            owner="acme",
            name="monitored",
            full_name="acme/monitored",
            monitoring_enabled=True,
        )
        session.add(repository)
        session.commit()

    calls: list[str] = []

    async def record_sync(_session, repository):  # type: ignore[no-untyped-def]
        calls.append(repository.id)

    monkeypatch.setattr("tracegate.studio.monitor.sync_repository_pull_requests", record_sync)
    monitor = RepositoryMonitor(database.session_factory, 60)
    assert await monitor.poll_once() == 0
    assert calls == []

    with database.session_factory() as session:
        settings = session.get(AppSettings, 1)
        assert settings is not None
        settings.background_monitoring = True
        session.commit()
    assert await monitor.poll_once() == 1
    assert len(calls) == 1
    snapshot = monitor.snapshot()
    assert snapshot.polling is False
    assert snapshot.last_started_at is not None
    assert snapshot.last_finished_at is not None
    assert monitor.configured_interval_seconds() == 60
    with database.session_factory() as session:
        settings = session.get(AppSettings, 1)
        assert settings is not None
        settings.github_poll_interval_seconds = 120
        session.commit()
    assert monitor.configured_interval_seconds() == 120
    database.dispose()


@pytest.mark.asyncio
async def test_monitor_honors_rate_limit_reset_before_retrying(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'rate-limit.db').as_posix()}"
    upgrade_database(database_url)
    database = StudioDatabase(database_url)
    with database.session_factory() as session:
        settings = session.get(AppSettings, 1)
        assert settings is not None
        settings.background_monitoring = True
        repository = Repository(
            owner="acme",
            name="limited",
            full_name="acme/limited",
            monitoring_enabled=True,
        )
        session.add(repository)
        session.commit()

    calls = 0
    reset_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    async def rate_limited(_session, _repository):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        raise GitHubAPIError(429, "rate limited", reset_at=reset_at)

    monkeypatch.setattr("tracegate.studio.monitor.sync_repository_pull_requests", rate_limited)
    monitor = RepositoryMonitor(database.session_factory, 30)
    try:
        assert await monitor.poll_once() == 0
        assert await monitor.poll_once() == 0
        assert calls == 1
        assert monitor.snapshot().rate_limited_until == reset_at
        assert "backoff" in (monitor.snapshot().last_error or "")
    finally:
        database.dispose()
