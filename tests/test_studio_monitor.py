from __future__ import annotations

from pathlib import Path

import pytest

from tracegate.studio.database import StudioDatabase
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import AppSettings, Repository
from tracegate.studio.monitor import RepositoryMonitor


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
    database.dispose()
