from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from tracegate.github import GitHubAPIError, GitHubNotModified, GitHubProvider

from .models import PullRequest, PullRequestSnapshot, Repository, RepositorySync


@dataclass(frozen=True)
class SyncResult:
    record: RepositorySync
    status: str
    changed_pull_requests: int


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def sync_repository_pull_requests(session: Session, repository: Repository) -> SyncResult:
    started = utcnow()
    record = RepositorySync(
        repository_id=repository.id,
        status="running",
        event_type="poll",
        started_at=started,
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    provider = GitHubProvider(token=token)
    try:
        try:
            pull_requests, etag, rate_limit = await provider.list_pull_requests(
                repository.owner,
                repository.name,
                state="all",
                etag=repository.sync_etag,
            )
        except GitHubNotModified as unchanged:
            repository.sync_etag = unchanged.etag
            repository.github_rate_remaining = unchanged.rate_limit.remaining
            repository.last_synced_at = utcnow()
            repository.connection_status = "ready"
            repository.last_error = None
            record.status = "not_modified"
            record.etag = unchanged.etag
            record.finished_at = utcnow()
            session.commit()
            return SyncResult(record, "not_modified", 0)

        changed = 0
        latest_commit: str | None = None
        for item in pull_requests:
            row = session.scalar(
                select(PullRequest).where(
                    PullRequest.repository_id == repository.id,
                    PullRequest.number == item.number,
                )
            )
            previous_head = row.head_sha if row else None
            if row is None:
                row = PullRequest(
                    repository_id=repository.id,
                    number=item.number,
                    title=item.title,
                    state=item.state,
                    url=item.html_url,
                )
                session.add(row)
                session.flush()
            row.title = item.title
            row.state = "merged" if item.merged_at else item.state
            row.url = item.html_url
            row.author = item.author
            row.base_sha = item.base_sha
            row.head_sha = item.head_sha
            row.draft = item.draft
            row.additions = item.additions
            row.deletions = item.deletions
            row.changed_files = item.changed_files
            row.updated_at_github = item.updated_at
            row.updated_at = utcnow()
            if previous_head != item.head_sha:
                changed += 1
                if previous_head is not None:
                    row.analysis_status = "not_analyzed"
            payload = item.model_dump(mode="json")
            payload_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            snapshot = session.scalar(
                select(PullRequestSnapshot).where(
                    PullRequestSnapshot.pull_request_id == row.id,
                    PullRequestSnapshot.head_sha == item.head_sha,
                    PullRequestSnapshot.payload_hash == payload_hash,
                )
            )
            if snapshot is None:
                session.add(
                    PullRequestSnapshot(
                        pull_request_id=row.id,
                        base_sha=item.base_sha,
                        head_sha=item.head_sha,
                        state=row.state,
                        payload_hash=payload_hash,
                    )
                )
            latest_commit = item.head_sha if latest_commit is None else latest_commit

        finished = utcnow()
        repository.sync_etag = etag
        repository.github_rate_remaining = rate_limit.remaining
        repository.last_synced_at = finished
        repository.connection_status = "ready"
        repository.last_error = None
        record.status = "completed"
        record.etag = etag
        record.commit_sha = latest_commit
        record.changed_count = changed
        record.finished_at = finished
        session.commit()
        session.refresh(record)
        return SyncResult(record, "completed", changed)
    except GitHubAPIError as exc:
        repository.connection_status = "error"
        repository.last_error = str(exc)
        record.status = "failed"
        record.error_code = f"github_http_{exc.status_code}"
        record.error_message = str(exc)
        record.finished_at = utcnow()
        session.commit()
        raise
    finally:
        await provider.close()
