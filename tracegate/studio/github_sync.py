from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from tracegate.github import GitHubAPIError, GitHubNotModified, GitHubProvider

from .models import (
    ChangedFileRecord,
    ChangedHunkRecord,
    CheckRunRecord,
    CommitRecord,
    PullRequest,
    PullRequestSnapshot,
    Repository,
    RepositorySync,
)


@dataclass(frozen=True)
class SyncResult:
    record: RepositorySync
    status: str
    changed_pull_requests: int
    changed_check_runs: int


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


FAILURE_CONCLUSIONS = {
    "action_required",
    "cancelled",
    "failure",
    "startup_failure",
    "stale",
    "timed_out",
}
_HUNK_HEADER = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$"
)


def _parse_hunks(patch: str) -> list[dict[str, object]]:
    hunks: list[dict[str, object]] = []
    current: list[str] = []
    header_match: re.Match[str] | None = None

    def finish() -> None:
        if header_match is None or not current:
            return
        encoded = "\n".join(current)
        hunks.append(
            {
                "header": current[0],
                "old_start": int(header_match.group(1)),
                "old_count": int(header_match.group(2) or 1),
                "new_start": int(header_match.group(3)),
                "new_count": int(header_match.group(4) or 1),
                "patch": encoded,
                "patch_hash": hashlib.sha256(encoded.encode()).hexdigest(),
            }
        )

    for line in patch.splitlines():
        match = _HUNK_HEADER.match(line)
        if match:
            finish()
            current = [line]
            header_match = match
        elif header_match is not None:
            current.append(line)
    finish()
    return hunks


async def _sync_pull_request_details(
    session: Session,
    provider: GitHubProvider,
    repository: Repository,
    pull_request: PullRequest,
) -> None:
    if not pull_request.head_sha:
        return
    files, commits = await asyncio.gather(
        provider.get_pull_request_files_data(repository.owner, repository.name, pull_request.number),
        provider.get_pull_request_commits_data(repository.owner, repository.name, pull_request.number),
    )
    existing_commits = {
        item.sha: item
        for item in session.scalars(
            select(CommitRecord).where(CommitRecord.pull_request_id == pull_request.id)
        )
    }
    seen_commits: set[str] = set()
    for position, item in enumerate(commits, start=1):
        seen_commits.add(item.sha)
        row = existing_commits.get(item.sha)
        if row is None:
            row = CommitRecord(pull_request_id=pull_request.id, sha=item.sha, message=item.message, position=position)
            session.add(row)
        row.message = item.message
        row.author_name = item.author_name
        row.author_email = item.author_email
        row.author_login = item.login
        row.authored_at = item.authored_at
        row.html_url = item.html_url
        row.position = position
        row.synced_at = utcnow()
    stale_commits = set(existing_commits) - seen_commits
    if stale_commits:
        session.execute(
            delete(CommitRecord).where(
                CommitRecord.pull_request_id == pull_request.id,
                CommitRecord.sha.in_(stale_commits),
            )
        )

    current_files = {
        item.path: item
        for item in session.scalars(
            select(ChangedFileRecord).where(
                ChangedFileRecord.pull_request_id == pull_request.id,
                ChangedFileRecord.head_sha == pull_request.head_sha,
            )
        )
    }
    seen_files: set[str] = set()
    for item in files:
        seen_files.add(item.filename)
        row = current_files.get(item.filename)
        patch_hash = hashlib.sha256(item.patch.encode()).hexdigest() if item.patch else None
        if row is None:
            row = ChangedFileRecord(
                pull_request_id=pull_request.id,
                head_sha=pull_request.head_sha,
                blob_sha=item.sha,
                path=item.filename,
                status=item.status,
            )
            session.add(row)
            session.flush()
        row.blob_sha = item.sha
        row.previous_path = item.previous_filename
        row.status = item.status
        row.additions = item.additions
        row.deletions = item.deletions
        row.changes = item.changes
        row.blob_url = item.blob_url
        row.raw_url = item.raw_url
        row.contents_url = item.contents_url
        row.patch = item.patch
        row.patch_hash = patch_hash
        row.synced_at = utcnow()
        session.execute(delete(ChangedHunkRecord).where(ChangedHunkRecord.changed_file_id == row.id))
        if item.patch:
            for sequence, hunk in enumerate(_parse_hunks(item.patch), start=1):
                session.add(ChangedHunkRecord(changed_file_id=row.id, sequence=sequence, **hunk))
    stale_files = set(current_files) - seen_files
    if stale_files:
        session.execute(
            delete(ChangedFileRecord).where(
                ChangedFileRecord.pull_request_id == pull_request.id,
                ChangedFileRecord.head_sha == pull_request.head_sha,
                ChangedFileRecord.path.in_(stale_files),
            )
        )


def _aggregate_check_status(runs: list[CheckRunRecord]) -> str:
    if not runs:
        return "not_available"
    if any(run.status != "completed" for run in runs):
        return "pending"
    if any(run.conclusion in FAILURE_CONCLUSIONS for run in runs):
        return "failure"
    if any(run.conclusion == "success" for run in runs):
        return "success"
    return "neutral"


async def _sync_open_pull_request_checks(
    session: Session,
    provider: GitHubProvider,
    repository: Repository,
) -> tuple[int, int | None]:
    pull_requests = list(
        session.scalars(
            select(PullRequest).where(
                PullRequest.repository_id == repository.id,
                PullRequest.state == "open",
                PullRequest.head_sha.is_not(None),
            )
        )
    )
    changed = 0
    rate_remaining: int | None = None
    for pull_request in pull_requests:
        assert pull_request.head_sha is not None
        try:
            remote_runs, etag, rate_limit = await provider.get_check_runs_page(
                repository.owner,
                repository.name,
                pull_request.head_sha,
                etag=pull_request.checks_etag,
            )
        except GitHubNotModified as unchanged:
            pull_request.checks_etag = unchanged.etag
            pull_request.last_checks_synced_at = utcnow()
            rate_remaining = unchanged.rate_limit.remaining
            continue

        rate_remaining = rate_limit.remaining
        existing = {
            run.github_id: run
            for run in session.scalars(
                select(CheckRunRecord).where(CheckRunRecord.pull_request_id == pull_request.id)
            )
        }
        seen: set[int] = set()
        for remote in remote_runs:
            seen.add(remote.id)
            run = existing.get(remote.id)
            if run is None:
                run = CheckRunRecord(
                    pull_request_id=pull_request.id,
                    github_id=remote.id,
                    head_sha=remote.head_sha,
                    name=remote.name,
                    status=remote.status,
                )
                session.add(run)
                changed += 1
            previous = (
                run.head_sha,
                run.name,
                run.status,
                run.conclusion,
                run.details_url,
                run.app_name,
                run.started_at,
                run.completed_at,
            )
            current = (
                remote.head_sha,
                remote.name,
                remote.status,
                remote.conclusion,
                remote.details_url,
                remote.app_name,
                remote.started_at,
                remote.completed_at,
            )
            if run.github_id in existing and previous != current:
                changed += 1
            (
                run.head_sha,
                run.name,
                run.status,
                run.conclusion,
                run.details_url,
                run.app_name,
                run.started_at,
                run.completed_at,
            ) = current
            run.synced_at = utcnow()

        removed_ids = set(existing) - seen
        if removed_ids:
            changed += len(removed_ids)
            session.execute(
                delete(CheckRunRecord).where(
                    CheckRunRecord.pull_request_id == pull_request.id,
                    CheckRunRecord.github_id.in_(removed_ids),
                )
            )
        session.flush()
        current_runs = list(
            session.scalars(
                select(CheckRunRecord).where(CheckRunRecord.pull_request_id == pull_request.id)
            )
        )
        pull_request.checks_status = _aggregate_check_status(current_runs)
        pull_request.checks_etag = etag
        pull_request.last_checks_synced_at = utcnow()
    return changed, rate_remaining


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
            checks_changed, checks_rate_remaining = await _sync_open_pull_request_checks(
                session, provider, repository
            )
            repository.sync_etag = unchanged.etag
            repository.github_rate_remaining = (
                checks_rate_remaining
                if checks_rate_remaining is not None
                else unchanged.rate_limit.remaining
            )
            repository.last_synced_at = utcnow()
            repository.connection_status = "ready"
            repository.last_error = None
            record.status = "completed" if checks_changed else "not_modified"
            record.etag = unchanged.etag
            record.checks_changed_count = checks_changed
            record.github_api_request_count = provider.request_count
            record.github_api_duration_ms = provider.total_latency_ms
            record.finished_at = utcnow()
            session.commit()
            return SyncResult(record, record.status, 0, checks_changed)

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
            previous_updated_at = row.updated_at_github if row else None
            if not {"additions", "deletions", "changed_files"} <= item.model_fields_set:
                item = await provider.get_pull_request(repository.owner, repository.name, item.number)
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
            row.base_ref = item.base_ref
            row.head_ref = item.head_ref
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
                    row.risk_level = None
                    row.risk_score = None
                    row.conclusion_summary = None
                    row.impact_paths_json = []
                    row.recommended_review_order_json = []
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
            if previous_head != item.head_sha or previous_updated_at != item.updated_at:
                await _sync_pull_request_details(session, provider, repository, row)

        session.flush()
        checks_changed, checks_rate_remaining = await _sync_open_pull_request_checks(
            session, provider, repository
        )
        finished = utcnow()
        repository.sync_etag = etag
        repository.github_rate_remaining = (
            checks_rate_remaining if checks_rate_remaining is not None else rate_limit.remaining
        )
        repository.last_synced_at = finished
        repository.connection_status = "ready"
        repository.last_error = None
        record.status = "completed"
        record.etag = etag
        record.commit_sha = latest_commit
        record.changed_count = changed
        record.checks_changed_count = checks_changed
        record.github_api_request_count = provider.request_count
        record.github_api_duration_ms = provider.total_latency_ms
        record.finished_at = finished
        session.commit()
        session.refresh(record)
        return SyncResult(record, "completed", changed, checks_changed)
    except GitHubAPIError as exc:
        repository.connection_status = "error"
        repository.last_error = str(exc)
        if exc.status_code == 429:
            repository.github_rate_remaining = 0
        record.status = "failed"
        record.error_code = f"github_http_{exc.status_code}"
        record.error_message = str(exc)
        record.github_api_request_count = provider.request_count
        record.github_api_duration_ms = provider.total_latency_ms
        record.finished_at = utcnow()
        session.commit()
        raise
    finally:
        await provider.close()
