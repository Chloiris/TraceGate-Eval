from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tracegate.github import GitHubAPIError

from .github_sync import sync_repository_pull_requests
from .models import AppSettings, Repository


logger = logging.getLogger("tracegate.studio.monitor")


@dataclass(frozen=True)
class MonitorSnapshot:
    running: bool
    polling: bool
    queued_repositories: int
    last_started_at: datetime | None
    last_finished_at: datetime | None
    last_error: str | None


class RepositoryMonitor:
    """Finite-interval local PR poller for explicitly monitored repositories."""

    def __init__(self, session_factory: sessionmaker[Session], interval_seconds: int) -> None:
        self.session_factory = session_factory
        self.interval_seconds = interval_seconds
        self._stop = asyncio.Event()
        self._wake = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._polling = False
        self._queued_repositories = 0
        self._last_started_at: datetime | None = None
        self._last_finished_at: datetime | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="tracegate-repository-monitor")

    def wake(self) -> None:
        self._wake.set()

    async def shutdown(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._task is not None:
            await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    def snapshot(self) -> MonitorSnapshot:
        return MonitorSnapshot(
            running=self._task is not None and not self._task.done(),
            polling=self._polling,
            queued_repositories=self._queued_repositories,
            last_started_at=self._last_started_at,
            last_finished_at=self._last_finished_at,
            last_error=self._last_error,
        )

    async def poll_once(self) -> int:
        with self.session_factory() as session:
            settings = session.get(AppSettings, 1)
            if settings is None or not settings.background_monitoring:
                self._queued_repositories = 0
                return 0
            repository_ids = list(
                session.scalars(
                    select(Repository.id)
                    .where(Repository.monitoring_enabled.is_(True))
                    .order_by(Repository.created_at)
                )
            )
        self._queued_repositories = len(repository_ids)
        if not repository_ids:
            return 0
        self._polling = True
        self._last_started_at = datetime.now(timezone.utc)
        self._last_error = None
        completed = 0
        try:
            for repository_id in repository_ids:
                if self._stop.is_set():
                    break
                with self.session_factory() as session:
                    repository = session.get(Repository, repository_id)
                    if repository is None or not repository.monitoring_enabled:
                        continue
                    try:
                        await sync_repository_pull_requests(session, repository)
                    except GitHubAPIError as exc:
                        self._last_error = f"{type(exc).__name__}: {exc}"
                        logger.warning(
                            "repository_poll_failed repository_id=%s error_type=%s",
                            repository_id,
                            type(exc).__name__,
                        )
                    else:
                        completed += 1
        finally:
            self._queued_repositories = 0
            self._polling = False
            self._last_finished_at = datetime.now(timezone.utc)
        return completed

    async def _run(self) -> None:
        while not self._stop.is_set():
            await self.poll_once()
            self._wake.clear()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self.interval_seconds)
            except TimeoutError:
                continue
