from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from tracegate.studio.models import FixConfirmation, FixSession

from .errors import AutofixError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def nonce_hash(nonce: str) -> str:
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ConfirmationGrant:
    confirmation_id: str
    nonce: str
    patch_hash: str
    expires_at: datetime


class FixConfirmationService:
    def issue(
        self,
        session: Session,
        fix_session: FixSession,
        *,
        patch_hash: str,
        ttl_seconds: int,
    ) -> ConfirmationGrant:
        if not 60 <= ttl_seconds <= 3600:
            raise AutofixError("fix_confirmation_required", "Confirmation TTL is outside policy")
        now = utcnow()
        for existing in session.scalars(
            select(FixConfirmation).where(
                FixConfirmation.fix_session_id == fix_session.id,
                FixConfirmation.consumed_at.is_(None),
                FixConfirmation.invalidated_at.is_(None),
            )
        ):
            existing.invalidated_at = now
        nonce = secrets.token_urlsafe(32)
        expires_at = now + timedelta(seconds=ttl_seconds)
        confirmation = FixConfirmation(
            fix_session_id=fix_session.id,
            repository_id=fix_session.repository_id,
            pull_request_id=fix_session.pull_request_id,
            finding_id=fix_session.finding_id,
            head_sha=fix_session.head_sha,
            patch_hash=patch_hash,
            nonce_hash=nonce_hash(nonce),
            expires_at=expires_at,
            confirmed_at=now,
        )
        session.add(confirmation)
        session.flush()
        return ConfirmationGrant(confirmation.id, nonce, patch_hash, expires_at)

    def consume(
        self,
        session: Session,
        fix_session: FixSession,
        *,
        patch_hash: str,
        nonce: str,
        current_head_sha: str,
    ) -> FixConfirmation:
        confirmation = session.scalar(
            select(FixConfirmation)
            .where(
                FixConfirmation.fix_session_id == fix_session.id,
                FixConfirmation.nonce_hash == nonce_hash(nonce),
            )
            .order_by(FixConfirmation.created_at.desc())
            .limit(1)
        )
        if confirmation is None or confirmation.confirmed_at is None:
            raise AutofixError("fix_confirmation_required", "Valid user confirmation is required")
        if confirmation.invalidated_at is not None:
            raise AutofixError("fix_confirmation_required", "Confirmation was invalidated")
        if confirmation.consumed_at is not None:
            raise AutofixError("fix_confirmation_consumed", "Confirmation was already consumed")
        if _aware(confirmation.expires_at) <= utcnow():
            raise AutofixError("fix_confirmation_expired", "Confirmation expired")
        if patch_hash != confirmation.patch_hash:
            raise AutofixError("fix_patch_hash_mismatch", "Confirmed Patch Hash does not match")
        if current_head_sha != confirmation.head_sha or fix_session.head_sha != confirmation.head_sha:
            raise AutofixError("fix_head_stale", "Pull Request Head changed after confirmation")
        if (
            confirmation.repository_id != fix_session.repository_id
            or confirmation.pull_request_id != fix_session.pull_request_id
            or confirmation.finding_id != fix_session.finding_id
        ):
            raise AutofixError("fix_confirmation_required", "Confirmation binding is inconsistent")
        confirmation.consumed_at = utcnow()
        session.flush()
        return confirmation

    def consume_bound(
        self,
        session: Session,
        fix_session: FixSession,
        *,
        patch_hash: str,
        current_head_sha: str,
    ) -> FixConfirmation:
        """Consume the newest server-issued confirmation without exposing its nonce.

        The authenticated confirmation request is the user gesture. The cryptographic
        nonce remains hash-only server state used to make each grant unique; it
        is deliberately absent from API responses and logs.
        """
        confirmation = session.scalar(
            select(FixConfirmation)
            .where(
                FixConfirmation.fix_session_id == fix_session.id,
                FixConfirmation.repository_id == fix_session.repository_id,
                FixConfirmation.pull_request_id == fix_session.pull_request_id,
                FixConfirmation.finding_id == fix_session.finding_id,
                FixConfirmation.head_sha == fix_session.head_sha,
                FixConfirmation.patch_hash == patch_hash,
                FixConfirmation.confirmed_at.is_not(None),
                FixConfirmation.consumed_at.is_(None),
                FixConfirmation.invalidated_at.is_(None),
            )
            .order_by(FixConfirmation.created_at.desc())
            .limit(1)
        )
        if confirmation is None:
            raise AutofixError("fix_confirmation_required", "Valid user confirmation is required")
        if _aware(confirmation.expires_at) <= utcnow():
            raise AutofixError("fix_confirmation_expired", "Confirmation expired")
        if current_head_sha != confirmation.head_sha or fix_session.head_sha != confirmation.head_sha:
            raise AutofixError("fix_head_stale", "Pull Request Head changed after confirmation")
        confirmation.consumed_at = utcnow()
        session.flush()
        return confirmation

    # Backwards-compatible descriptive alias for callers that use the lifecycle wording.
    consume_latest = consume_bound

    def invalidate(self, session: Session, fix_session_id: str) -> int:
        now = utcnow()
        count = 0
        for confirmation in session.scalars(
            select(FixConfirmation).where(
                FixConfirmation.fix_session_id == fix_session_id,
                FixConfirmation.consumed_at.is_(None),
                FixConfirmation.invalidated_at.is_(None),
            )
        ):
            confirmation.invalidated_at = now
            count += 1
        session.flush()
        return count
