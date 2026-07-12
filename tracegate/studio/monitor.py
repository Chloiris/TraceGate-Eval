from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tracegate.github import GitHubAPIError

from .github_sync import sync_repository_pull_requests
from .models import AppSettings, Repository
from .run_manager import RunManager


logger = logging.getLogger("tracegate.studio.monitor")


@dataclass(frozen=True)
class MonitorSnapshot:
    running: bool
    polling: bool
    queued_repositories: int
    last_started_at: datetime | None
    last_finished_at: datetime | None
    last_error: str | None
    rate_limited_until: datetime | None


class RepositoryMonitor:
    """Finite-interval local PR poller for explicitly monitored repositories."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        interval_seconds: int,
        run_manager: RunManager | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.default_interval_seconds = interval_seconds
        self.run_manager = run_manager
        self._stop = asyncio.Event()
        self._wake = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._polling = False
        self._queued_repositories = 0
        self._last_started_at: datetime | None = None
        self._last_finished_at: datetime | None = None
        self._last_error: str | None = None
        self._rate_limited_until: datetime | None = None

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
            rate_limited_until=self._rate_limited_until,
        )

    async def poll_once(self) -> int:
        now = datetime.now(timezone.utc)
        if self._rate_limited_until is not None and now < self._rate_limited_until:
            self._last_error = f"GitHub rate limit backoff until {self._rate_limited_until.isoformat()}"
            return 0
        self._rate_limited_until = None
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
                        if exc.status_code == 429:
                            self._rate_limited_until = exc.reset_at or (
                                datetime.now(timezone.utc)
                                + timedelta(seconds=max(60, self.configured_interval_seconds()))
                            )
                        logger.warning(
                            "repository_poll_failed repository_id=%s error_type=%s",
                            repository_id,
                            type(exc).__name__,
                        )
                        if exc.status_code == 429:
                            break
                    else:
                        if self.run_manager is not None:
                            automatic = self.run_manager.enqueue_automatic(repository_id)
                            if automatic.skipped_reason:
                                self._last_error = automatic.skipped_reason
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
                await asyncio.wait_for(self._wake.wait(), timeout=self.configured_interval_seconds())
            except TimeoutError:
                continue

    def configured_interval_seconds(self) -> int:
        """Read the persisted interval for every wait so Settings changes apply immediately."""
        with self.session_factory() as session:
            settings = session.get(AppSettings, 1)
            if settings is None:
                return self.default_interval_seconds
            return settings.github_poll_interval_seconds
