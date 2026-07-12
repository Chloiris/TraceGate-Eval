from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, TypeVar

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from tracegate.autofix.confirmation import FixConfirmationService
from tracegate.autofix.errors import AutofixError
from tracegate.autofix.schemas import FixPermissionMode, FixSessionStatus
from tracegate.autofix.state_machine import ensure_transition
from tracegate.autofix.workspace import FixWorkspaceManager
from tracegate.models import ModelConfigurationError
from tracegate.tools import create_read_only_registry

from .models import (
    AppSettings,
    FixConfirmation,
    FixEvent,
    FixSession,
    PatchProposalRecord,
    PullRequest,
    Repository,
)
from .run_manager import configured_model


T = TypeVar("T")
_IDEMPOTENCY_KEY = re.compile(r"^[^\r\n]{8,200}$")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FixWorkflow(Protocol):
    async def initialize(
        self,
        finding_id: str,
        permission_mode: str = FixPermissionMode.PROPOSE_ONLY.value,
    ) -> str: ...

    async def plan(self, session_id: str, force_eligibility: bool = False) -> object: ...

    async def generate(self, session_id: str) -> object: ...

    async def apply(self, session_id: str, patch_hash: str) -> object: ...

    async def validate(self, session_id: str) -> object: ...

    async def re_review(self, session_id: str) -> object: ...


WorkflowFactory = Callable[[], FixWorkflow]
ModelFactory = Callable[[Session], object]


class FixManagerError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


@dataclass
class _IdempotencyRecord:
    fingerprint: str
    future: asyncio.Future[Any]


class IdempotencyStore:
    """Process-local request coalescing for the loopback-only Studio API.

    Fix state itself remains authoritative in the database. This store prevents
    retries from duplicating an in-flight or already successful local request.
    """

    def __init__(self, *, max_records: int = 2_048) -> None:
        self.max_records = max_records
        self._records: dict[tuple[str, str], _IdempotencyRecord] = {}
        self._order: list[tuple[str, str]] = []
        self._lock = asyncio.Lock()

    async def execute(
        self,
        scope: str,
        key: str | None,
        payload: object,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        if key is None:
            return await operation()
        normalized = key.strip()
        if not _IDEMPOTENCY_KEY.fullmatch(normalized):
            raise FixManagerError(
                400,
                "fix_idempotency_key_invalid",
                "Idempotency-Key must contain between 8 and 200 characters without newlines.",
            )
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        record_key = (scope, normalized)
        async with self._lock:
            existing = self._records.get(record_key)
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise FixManagerError(
                        409,
                        "fix_idempotency_conflict",
                        "Idempotency-Key was already used with a different request body.",
                    )
                future = existing.future
                owner = False
            else:
                future = asyncio.get_running_loop().create_future()
                self._records[record_key] = _IdempotencyRecord(fingerprint, future)
                self._order.append(record_key)
                self._trim_locked()
                owner = True
        if not owner:
            return await asyncio.shield(future)
        try:
            result = await operation()
        except BaseException as exc:
            if not future.done():
                future.set_exception(exc)
                # Retrieve it here as well so a request without a coalesced waiter
                # cannot produce an "exception was never retrieved" warning.
                future.exception()
            async with self._lock:
                self._records.pop(record_key, None)
                if record_key in self._order:
                    self._order.remove(record_key)
            raise
        if not future.done():
            future.set_result(result)
        return result

    def _trim_locked(self) -> None:
        while len(self._order) > self.max_records:
            oldest = self._order.pop(0)
            record = self._records.get(oldest)
            if record is not None and record.future.done():
                self._records.pop(oldest, None)
            else:
                self._order.append(oldest)
                break


class FixManager:
    """Serializes mutations and owns controlled Fix workspace lifecycle."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        workspace_manager: FixWorkspaceManager,
        *,
        workflow_factory: WorkflowFactory | None = None,
        model_factory: ModelFactory = configured_model,
    ) -> None:
        self.session_factory = session_factory
        self.workspace_manager = workspace_manager
        self._provided_workflow_factory = workflow_factory
        self.model_factory = model_factory
        self.confirmations = FixConfirmationService()
        self.idempotency = IdempotencyStore()
        self._locks: dict[str, asyncio.Lock] = {}
        self._active: dict[str, asyncio.Task[object]] = {}

    async def initialize(
        self,
        *,
        finding_id: str,
        permission_mode: str,
    ) -> str:
        workflow = self._new_workflow()
        try:
            result = await _await_if_needed(workflow.initialize(finding_id, permission_mode))
        except AutofixError as exc:
            raise _manager_error(exc) from exc
        except Exception as exc:
            raise FixManagerError(
                500,
                "fix_workflow_failed",
                f"Fix workflow initialization failed ({type(exc).__name__}).",
            ) from exc
        if isinstance(result, str):
            return result
        if isinstance(result, dict) and isinstance(result.get("fix_session_id"), str):
            return result["fix_session_id"]
        raise FixManagerError(500, "fix_workflow_invalid_result", "Fix workflow did not return a session ID.")

    async def plan(
        self,
        session_id: str,
        *,
        expected_lock_version: int,
        force_eligibility: bool,
    ) -> str:
        return await self._run_workflow_action(
            session_id,
            expected_lock_version,
            "plan",
            lambda workflow: workflow.plan(session_id, force_eligibility),
        )

    async def generate(self, session_id: str, *, expected_lock_version: int) -> str:
        return await self._run_workflow_action(
            session_id,
            expected_lock_version,
            "generate",
            lambda workflow: workflow.generate(session_id),
        )

    async def confirm(
        self,
        session_id: str,
        *,
        expected_lock_version: int,
        patch_hash: str,
    ) -> str:
        async with self._session_lock(session_id):
            self._ensure_not_active(session_id)
            with self.session_factory() as session:
                fix_session = self._reserve_in_session(session, session_id, expected_lock_version)
                if fix_session.status != FixSessionStatus.AWAITING_USER_CONFIRMATION.value:
                    raise FixManagerError(
                        409,
                        "fix_invalid_transition",
                        "Fix Session is not awaiting user confirmation.",
                    )
                if fix_session.permission_mode != FixPermissionMode.APPLY_IN_ISOLATED_WORKSPACE.value:
                    raise FixManagerError(
                        409,
                        "fix_permission_denied",
                        "This Fix Session is proposal-only and cannot apply a patch.",
                    )
                proposal = _latest_proposal(session, session_id)
                if proposal is None:
                    raise FixManagerError(409, "fix_patch_missing", "No Patch Proposal is available.")
                if proposal.stale_at is not None or proposal.patch_hash != patch_hash:
                    raise FixManagerError(
                        409,
                        "fix_patch_hash_mismatch",
                        "The displayed Patch Hash no longer matches the current proposal.",
                    )
                if proposal.head_sha != fix_session.head_sha:
                    raise FixManagerError(409, "fix_head_stale", "Pull Request Head changed before confirmation.")
                pull_request = session.get(PullRequest, fix_session.pull_request_id)
                if pull_request is None or pull_request.head_sha != fix_session.head_sha:
                    now = utcnow()
                    proposal.stale_at = now
                    fix_session.status = FixSessionStatus.STALE.value
                    fix_session.current_node = None
                    fix_session.error_code = "fix_head_stale"
                    fix_session.error_message = "Pull Request Head changed before confirmation."
                    fix_session.finished_at = now
                    self._append_event(
                        session,
                        fix_session,
                        "terminal",
                        {
                            "status": "STALE",
                            "error_code": "fix_head_stale",
                            "error_message": fix_session.error_message,
                        },
                    )
                    session.commit()
                    raise FixManagerError(
                        409,
                        "fix_head_stale",
                        "Pull Request Head changed before confirmation; regenerate from the new Head.",
                    )
                settings = session.get(AppSettings, 1)
                ttl = settings.autofix_confirmation_ttl_seconds if settings is not None else 900
                self.confirmations.issue(session, fix_session, patch_hash=patch_hash, ttl_seconds=ttl)
                self._append_event(
                    session,
                    fix_session,
                    "workflow_step",
                    {
                        "status": fix_session.status,
                        "current_node": fix_session.current_node,
                        "message": "Patch Hash confirmed for one isolated apply attempt.",
                    },
                )
                session.commit()
        return session_id

    async def apply(
        self,
        session_id: str,
        *,
        expected_lock_version: int,
        patch_hash: str,
    ) -> str:
        return await self._run_workflow_action(
            session_id,
            expected_lock_version,
            "apply",
            lambda workflow: workflow.apply(session_id, patch_hash),
            patch_hash=patch_hash,
            require_confirmation=True,
        )

    async def validate(self, session_id: str, *, expected_lock_version: int) -> str:
        return await self._run_workflow_action(
            session_id,
            expected_lock_version,
            "validate",
            lambda workflow: workflow.validate(session_id),
        )

    async def re_review(self, session_id: str, *, expected_lock_version: int) -> str:
        return await self._run_workflow_action(
            session_id,
            expected_lock_version,
            "re_review",
            lambda workflow: workflow.re_review(session_id),
        )

    async def cancel(self, session_id: str, *, expected_lock_version: int) -> str:
        active: asyncio.Task[object] | None
        async with self._session_lock(session_id):
            with self.session_factory() as session:
                fix_session = self._reserve_in_session(session, session_id, expected_lock_version)
                try:
                    ensure_transition(fix_session.status, FixSessionStatus.CANCELLED)
                except AutofixError as exc:
                    raise _manager_error(exc) from exc
                fix_session.cancellation_requested = True
                fix_session.status = FixSessionStatus.CANCELLED.value
                fix_session.current_node = None
                fix_session.finished_at = utcnow()
                self.confirmations.invalidate(session, session_id)
                self._append_event(
                    session,
                    fix_session,
                    "terminal",
                    {"status": "CANCELLED", "error_code": None, "error_message": None},
                )
                session.commit()
            active = self._active.get(session_id)
            if active is not None and not active.done():
                active.cancel()
        if active is not None and not active.done():
            await asyncio.gather(active, return_exceptions=True)
        return session_id

    async def rollback(self, session_id: str, *, expected_lock_version: int) -> str:
        async with self._session_lock(session_id):
            self._ensure_not_active(session_id)
            with self.session_factory() as session:
                fix_session = self._reserve_in_session(session, session_id, expected_lock_version)
                try:
                    ensure_transition(fix_session.status, FixSessionStatus.ROLLED_BACK)
                except AutofixError as exc:
                    raise _manager_error(exc) from exc
                repository = session.get(Repository, fix_session.repository_id)
                workspace = self._load_workspace(fix_session, repository)
                await asyncio.to_thread(self.workspace_manager.rollback, workspace)
                fix_session.status = FixSessionStatus.ROLLED_BACK.value
                fix_session.current_node = None
                fix_session.finished_at = utcnow()
                fix_session.cleanup_status = "ACTIVE"
                self.confirmations.invalidate(session, session_id)
                self._append_event(
                    session,
                    fix_session,
                    "terminal",
                    {"status": "ROLLED_BACK", "error_code": None, "error_message": None},
                )
                session.commit()
        return session_id

    async def delete_workspace(self, session_id: str, *, expected_lock_version: int) -> None:
        async with self._session_lock(session_id):
            self._ensure_not_active(session_id)
            with self.session_factory() as session:
                fix_session = self._reserve_in_session(session, session_id, expected_lock_version)
                if fix_session.status not in {
                    FixSessionStatus.FAILED.value,
                    FixSessionStatus.CANCELLED.value,
                    FixSessionStatus.ROLLED_BACK.value,
                    FixSessionStatus.STALE.value,
                }:
                    raise FixManagerError(
                        409,
                        "fix_invalid_transition",
                        "Cancel or rollback the Fix Session before deleting its workspace.",
                    )
                if fix_session.workspace_path is not None:
                    repository = session.get(Repository, fix_session.repository_id)
                    workspace = self._load_workspace(fix_session, repository)
                    fix_session.cleanup_status = "CLEANUP_PENDING"
                    session.flush()
                    try:
                        await asyncio.to_thread(self.workspace_manager.delete, workspace)
                    except Exception:
                        fix_session.cleanup_status = "CLEANUP_FAILED"
                        session.commit()
                        raise
                fix_session.workspace_path = None
                fix_session.cleanup_status = "DELETED"
                self._append_event(
                    session,
                    fix_session,
                    "workflow_step",
                    {
                        "status": fix_session.status,
                        "current_node": fix_session.current_node,
                        "message": "Isolated Fix workspace deleted.",
                    },
                )
                session.commit()

    async def cleanup_diagnostic_workspace(self, session_id: str) -> None:
        """Delete one managed residual workspace selected from Diagnostics.

        A persisted Fix Session is cleaned through the normal, repository-aware
        path.  A truly orphaned directory is removed only after the workspace
        manager verifies the exact managed-root layout and rejects symlinks.
        """

        async with self._session_lock(session_id):
            self._ensure_not_active(session_id)
            with self.session_factory() as session:
                fix_session = session.get(FixSession, session_id)
                if fix_session is not None and fix_session.workspace_path is not None:
                    fix_session = self._reserve_in_session(
                        session,
                        session_id,
                        fix_session.lock_version,
                    )
                    repository = session.get(Repository, fix_session.repository_id)
                    workspace = self._load_workspace(fix_session, repository)
                    current = FixSessionStatus(fix_session.status)
                    if current not in {
                        FixSessionStatus.FAILED,
                        FixSessionStatus.CANCELLED,
                        FixSessionStatus.ROLLED_BACK,
                        FixSessionStatus.STALE,
                    }:
                        post_apply = current in {
                            FixSessionStatus.APPLYING_PATCH,
                            FixSessionStatus.PATCH_APPLIED,
                            FixSessionStatus.RUNNING_VALIDATION,
                            FixSessionStatus.VALIDATION_COMPLETE,
                            FixSessionStatus.REINDEXING_CHANGES,
                            FixSessionStatus.RE_REVIEWING,
                            FixSessionStatus.FINALIZING,
                            FixSessionStatus.COMPLETED,
                        }
                        if post_apply:
                            await asyncio.to_thread(
                                self.workspace_manager.rollback, workspace
                            )
                        target = (
                            FixSessionStatus.CANCELLED
                            if current == FixSessionStatus.APPLYING_PATCH
                            or not post_apply
                            else FixSessionStatus.ROLLED_BACK
                        )
                        ensure_transition(current, target)
                        fix_session.status = target.value
                        fix_session.current_node = None
                        fix_session.finished_at = utcnow()
                        fix_session.cancellation_requested = (
                            target == FixSessionStatus.CANCELLED
                        )
                        self.confirmations.invalidate(session, session_id)
                        self._append_event(
                            session,
                            fix_session,
                            "terminal",
                            {
                                "status": target.value,
                                "error_code": None,
                                "error_message": None,
                            },
                        )
                    fix_session.cleanup_status = "CLEANUP_PENDING"
                    session.flush()
                    try:
                        await asyncio.to_thread(self.workspace_manager.delete, workspace)
                    except Exception:
                        fix_session.cleanup_status = "CLEANUP_FAILED"
                        session.commit()
                        raise
                    fix_session.workspace_path = None
                    fix_session.cleanup_status = "DELETED"
                    self._append_event(
                        session,
                        fix_session,
                        "workflow_step",
                        {
                            "status": fix_session.status,
                            "current_node": fix_session.current_node,
                            "message": "Residual isolated Fix workspace deleted from Diagnostics.",
                        },
                    )
                    session.commit()
                    return

            candidates = [
                path
                for path in self.workspace_manager.discover_residual_worktrees()
                if path.parent.name == session_id
            ]
            if not candidates:
                raise FixManagerError(
                    404,
                    "fix_workspace_not_found",
                    "Managed residual Fix workspace was not found.",
                )
            if len(candidates) != 1:
                raise FixManagerError(
                    409,
                    "fix_workspace_ambiguous",
                    "More than one managed residual Fix workspace has this session identifier.",
                )
            await asyncio.to_thread(
                self.workspace_manager.delete_residual_worktree,
                candidates[0],
            )

    async def shutdown(self) -> None:
        tasks = [task for task in self._active.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._active.clear()

    async def _run_workflow_action(
        self,
        session_id: str,
        expected_lock_version: int,
        action: str,
        call: Callable[[FixWorkflow], Awaitable[object] | object],
        *,
        patch_hash: str | None = None,
        require_confirmation: bool = False,
    ) -> str:
        async with self._session_lock(session_id):
            self._ensure_not_active(session_id)
            with self.session_factory() as session:
                fix_session = self._reserve_in_session(session, session_id, expected_lock_version)
                required_statuses = {
                    "plan": {
                        FixSessionStatus.CREATED.value,
                        FixSessionStatus.ELIGIBLE.value,
                    },
                    "generate": {FixSessionStatus.PLAN_READY.value},
                    "apply": {FixSessionStatus.AWAITING_USER_CONFIRMATION.value},
                    "validate": {FixSessionStatus.PATCH_APPLIED.value},
                    "re_review": {FixSessionStatus.VALIDATION_COMPLETE.value},
                }.get(action)
                if (
                    required_statuses is not None
                    and fix_session.status not in required_statuses
                ):
                    raise FixManagerError(
                        409,
                        "fix_invalid_transition",
                        f"Action {action} is not available while Fix Session is {fix_session.status}.",
                    )
                if patch_hash is not None:
                    proposal = _latest_proposal(session, session_id)
                    if proposal is None or proposal.stale_at is not None:
                        raise FixManagerError(409, "fix_patch_missing", "No current Patch Proposal is available.")
                    if proposal.patch_hash != patch_hash or proposal.head_sha != fix_session.head_sha:
                        raise FixManagerError(
                            409,
                            "fix_patch_hash_mismatch",
                            "Patch Hash or Head SHA no longer matches the current proposal.",
                        )
                    if require_confirmation and not _has_live_confirmation(
                        session, fix_session, patch_hash
                    ):
                        raise FixManagerError(
                            409,
                            "fix_confirmation_required",
                            "Confirm the current Patch Hash before applying it.",
                        )
                session.commit()
            workflow = self._new_workflow()
            task = asyncio.create_task(
                _await_if_needed(call(workflow)),
                name=f"tracegate-fix-{action}-{session_id}",
            )
            self._active[session_id] = task
        try:
            await task
        except asyncio.CancelledError as exc:
            raise FixManagerError(409, "fix_cancelled", "Fix Session action was cancelled.") from exc
        except AutofixError as exc:
            raise _manager_error(exc) from exc
        except FixManagerError:
            raise
        except Exception as exc:
            raise FixManagerError(
                500,
                "fix_workflow_failed",
                f"Fix workflow action failed ({type(exc).__name__}).",
            ) from exc
        finally:
            async with self._session_lock(session_id):
                if self._active.get(session_id) is task:
                    self._active.pop(session_id, None)
        return session_id

    def _new_workflow(self) -> FixWorkflow:
        if self._provided_workflow_factory is not None:
            return self._provided_workflow_factory()
        try:
            from tracegate.agent.fix_workflow import TraceGateFixWorkflow
        except ImportError as exc:
            raise FixManagerError(
                503,
                "fix_workflow_unavailable",
                "Coding Agent Autofix workflow is unavailable in this build.",
            ) from exc
        try:
            with self.session_factory() as session:
                model = self.model_factory(session)
                settings = session.get(AppSettings, 1)
                disabled_tools = set(settings.disabled_tools_json) if settings is not None else set()
        except ModelConfigurationError as exc:
            raise FixManagerError(503, "model_not_configured", str(exc)) from exc
        return TraceGateFixWorkflow(
            self.session_factory,
            model,
            create_read_only_registry(disabled_tools),
            self.workspace_manager,
        )

    def _reserve_in_session(
        self,
        session: Session,
        session_id: str,
        expected_lock_version: int,
    ) -> FixSession:
        now = utcnow()
        result = session.execute(
            update(FixSession)
            .where(
                FixSession.id == session_id,
                FixSession.lock_version == expected_lock_version,
            )
            .values(
                lock_version=expected_lock_version + 1,
                last_active_at=now,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            session.rollback()
            existing = session.get(FixSession, session_id)
            if existing is None:
                raise FixManagerError(404, "fix_session_not_found", "Fix Session was not found.")
            raise FixManagerError(
                409,
                "fix_lock_conflict",
                f"Fix Session changed; refresh and retry with lock_version {existing.lock_version}.",
            )
        session.expire_all()
        fix_session = session.get(FixSession, session_id)
        if fix_session is None:
            raise FixManagerError(404, "fix_session_not_found", "Fix Session was not found.")
        return fix_session

    def _append_event(
        self,
        session: Session,
        fix_session: FixSession,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        sequence = session.scalar(
            select(func.max(FixEvent.sequence)).where(FixEvent.fix_session_id == fix_session.id)
        )
        session.add(
            FixEvent(
                fix_session_id=fix_session.id,
                sequence=(sequence or 0) + 1,
                event_type=event_type,
                payload_json=payload,
            )
        )

    def _load_workspace(
        self,
        fix_session: FixSession,
        repository: Repository | None,
    ):
        if repository is None or not repository.local_path or not fix_session.workspace_path:
            raise FixManagerError(
                409,
                "fix_workspace_unavailable",
                "This Fix Session has no active isolated workspace.",
            )
        return self.workspace_manager.load(
            session_id=fix_session.id,
            repository_id=fix_session.repository_id,
            source_root=Path(repository.local_path),
            head_sha=fix_session.head_sha,
        )

    def _ensure_not_active(self, session_id: str) -> None:
        task = self._active.get(session_id)
        if task is not None and not task.done():
            raise FixManagerError(409, "fix_session_busy", "Fix Session already has an active action.")

    def _session_lock(self, session_id: str) -> asyncio.Lock:
        return self._locks.setdefault(session_id, asyncio.Lock())


def _latest_proposal(session: Session, session_id: str) -> PatchProposalRecord | None:
    return session.scalar(
        select(PatchProposalRecord)
        .where(PatchProposalRecord.fix_session_id == session_id)
        .order_by(PatchProposalRecord.proposal_version.desc())
        .limit(1)
    )


def _has_live_confirmation(
    session: Session,
    fix_session: FixSession,
    patch_hash: str,
) -> bool:
    now = utcnow()
    return session.scalar(
        select(FixConfirmation.id)
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
            FixConfirmation.expires_at > now,
        )
        .limit(1)
    ) is not None


async def _await_if_needed(value: Awaitable[T] | T) -> T:
    if inspect.isawaitable(value):
        return await value
    return value


def _manager_error(exc: AutofixError) -> FixManagerError:
    if exc.code in {"fix_session_not_found", "fix_finding_not_found"}:
        status = 404
    elif exc.code in {
        "fix_patch_unsafe",
        "fix_validation_forbidden",
        "fix_validation_command_invalid",
    }:
        status = 422
    elif exc.code in {"fix_workspace_unavailable", "fix_model_unavailable"}:
        status = 503
    else:
        status = 409
    return FixManagerError(status, exc.code, str(exc))
