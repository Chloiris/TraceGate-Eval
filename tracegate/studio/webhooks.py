from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tracegate.github import PullRequestData

from .errors import StudioAPIError
from .models import PullRequest, PullRequestSnapshot, Repository, WebhookDelivery


MAX_WEBHOOK_BYTES = 2 * 1024 * 1024
_DELIVERY_ID = re.compile(r"^[A-Za-z0-9-]{1,128}$")
router = APIRouter(prefix="/api/v1/webhooks")


class WebhookResponse(BaseModel):
    accepted: bool
    duplicate: bool
    status: str


def _session(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.database.session_factory()
    try:
        yield session
    finally:
        session.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_signature(body: bytes, signature: str | None) -> None:
    secret = os.environ.get("TRACEGATE_GITHUB_WEBHOOK_SECRET")
    if not secret:
        raise StudioAPIError(
            503,
            "webhook_relay_not_configured",
            "Webhook Relay 未配置",
        )
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if signature is None or not hmac.compare_digest(signature, expected):
        raise StudioAPIError(401, "invalid_webhook_signature", "GitHub webhook signature is invalid.")


@router.post("/github", response_model=WebhookResponse)
async def github_webhook(
    request: Request,
    session: Annotated[Session, Depends(_session)],
    x_github_delivery: Annotated[str | None, Header()] = None,
    x_github_event: Annotated[str | None, Header()] = None,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> WebhookResponse:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            parsed_content_length = int(content_length)
            if parsed_content_length < 0:
                raise ValueError("negative content length")
            if parsed_content_length > MAX_WEBHOOK_BYTES:
                raise StudioAPIError(413, "webhook_too_large", "GitHub webhook exceeded 2 MiB.")
        except ValueError as exc:
            raise StudioAPIError(400, "invalid_content_length", "Content-Length is invalid.") from exc
    body = await request.body()
    if len(body) > MAX_WEBHOOK_BYTES:
        raise StudioAPIError(413, "webhook_too_large", "GitHub webhook exceeded 2 MiB.")
    _validate_signature(body, x_hub_signature_256)
    if x_github_delivery is None or not _DELIVERY_ID.fullmatch(x_github_delivery):
        raise StudioAPIError(422, "invalid_delivery_id", "X-GitHub-Delivery is required and invalid.")
    if not x_github_event or len(x_github_event) > 128:
        raise StudioAPIError(422, "invalid_webhook_event", "X-GitHub-Event is required and invalid.")
    payload_hash = hashlib.sha256(body).hexdigest()
    existing = session.scalar(
        select(WebhookDelivery).where(WebhookDelivery.delivery_id == x_github_delivery)
    )
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise StudioAPIError(
                409,
                "webhook_delivery_mismatch",
                "A delivery ID was replayed with different content.",
            )
        return WebhookResponse(accepted=True, duplicate=True, status=existing.status)
    record = WebhookDelivery(
        delivery_id=x_github_delivery,
        event=x_github_event,
        payload_hash=payload_hash,
        status="received",
    )
    session.add(record)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(WebhookDelivery).where(WebhookDelivery.delivery_id == x_github_delivery)
        )
        if existing is None or existing.payload_hash != payload_hash:
            raise StudioAPIError(409, "webhook_delivery_conflict", "Webhook delivery conflict.")
        return WebhookResponse(accepted=True, duplicate=True, status=existing.status)

    if x_github_event != "pull_request":
        record.status = "ignored_event"
        record.processed_at = _now()
        session.commit()
        return WebhookResponse(accepted=True, duplicate=False, status=record.status)
    try:
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        repository_payload = payload.get("repository")
        pull_request_payload = payload.get("pull_request")
        if not isinstance(repository_payload, dict) or not isinstance(pull_request_payload, dict):
            raise ValueError("repository and pull_request objects are required")
        full_name = repository_payload.get("full_name")
        if not isinstance(full_name, str):
            raise ValueError("repository.full_name is required")
        item = PullRequestData.model_validate(pull_request_payload)
    except (json.JSONDecodeError, ValueError) as exc:
        record.status = "invalid_payload"
        record.error_message = f"{type(exc).__name__}: payload validation failed"
        record.processed_at = _now()
        session.commit()
        raise StudioAPIError(422, "invalid_webhook_payload", "GitHub webhook payload is invalid.") from exc

    record.repository_full_name = full_name
    record.pull_request_number = item.number
    repository = session.scalar(select(Repository).where(Repository.full_name == full_name))
    if repository is None:
        record.status = "ignored_repository"
        record.processed_at = _now()
        session.commit()
        return WebhookResponse(accepted=True, duplicate=False, status=record.status)
    pull_request = session.scalar(
        select(PullRequest).where(
            PullRequest.repository_id == repository.id,
            PullRequest.number == item.number,
        )
    )
    previous_head = pull_request.head_sha if pull_request else None
    if pull_request is None:
        pull_request = PullRequest(
            repository_id=repository.id,
            number=item.number,
            title=item.title,
            state=item.state,
            url=item.html_url,
        )
        session.add(pull_request)
        session.flush()
    pull_request.title = item.title
    pull_request.state = "merged" if item.merged_at else item.state
    pull_request.url = item.html_url
    pull_request.author = item.author
    pull_request.base_ref = item.base_ref
    pull_request.head_ref = item.head_ref
    pull_request.base_sha = item.base_sha
    pull_request.head_sha = item.head_sha
    pull_request.draft = item.draft
    pull_request.additions = item.additions
    pull_request.deletions = item.deletions
    pull_request.changed_files = item.changed_files
    pull_request.updated_at_github = item.updated_at
    pull_request.updated_at = _now()
    if previous_head != item.head_sha:
        pull_request.analysis_status = "not_analyzed"
    snapshot = session.scalar(
        select(PullRequestSnapshot).where(
            PullRequestSnapshot.pull_request_id == pull_request.id,
            PullRequestSnapshot.head_sha == item.head_sha,
            PullRequestSnapshot.payload_hash == payload_hash,
        )
    )
    if snapshot is None:
        session.add(
            PullRequestSnapshot(
                pull_request_id=pull_request.id,
                base_sha=item.base_sha,
                head_sha=item.head_sha,
                state=pull_request.state,
                payload_hash=payload_hash,
            )
        )
    repository.connection_status = "ready"
    repository.last_synced_at = _now()
    repository.last_error = None
    record.status = "processed"
    record.processed_at = _now()
    session.commit()
    request.app.state.repository_monitor.wake()
    return WebhookResponse(accepted=True, duplicate=False, status=record.status)
