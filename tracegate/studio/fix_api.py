from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracegate.autofix.errors import AutofixError
from tracegate.autofix.patch_safety import compute_patch_hash
from tracegate.autofix.schemas import (
    FixEligibilityResult,
    FixPermissionMode,
    FixPlan,
    FixResolution,
    FixSessionStatus,
    PatchInspection,
    PostFixReport,
    ReReviewAssessment,
    ValidationCommand,
    ValidationPlan,
    ValidationStatus,
)
from tracegate.autofix.state_machine import allowed_actions
from tracegate.repository import RepositoryPathError

from .errors import StudioAPIError
from .fix_manager import FixManager, FixManagerError
from .models import (
    AppSettings,
    FixConfirmation,
    FixEvent,
    FixResult,
    FixSession,
    FixStep,
    FixToolCallRecord,
    PatchProposalRecord,
    Repository,
    ValidationRun,
)
from .security import require_local_token


router = APIRouter(
    prefix="/api/v1/fix-sessions",
    dependencies=[Depends(require_local_token)],
)
workspace_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_local_token)])

T = TypeVar("T")
_TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "ROLLED_BACK", "STALE"}
_EVENT_TYPES = {
    "session",
    "workflow_step",
    "patch_ready",
    "validation_started",
    "validation_output",
    "validation_finished",
    "re_review",
    "report",
    "terminal",
    "error",
}
_ACTION_NAMES = {
    "plan": "PLAN",
    "generate": "GENERATE",
    "confirm": "CONFIRM",
    "apply": "APPLY",
    "validate": "VALIDATE",
    "re_review": "RE_REVIEW",
    "cancel": "CANCEL",
    "rollback": "ROLLBACK",
    "delete_workspace": "DELETE_WORKSPACE",
    "export_patch": "EXPORT_PATCH",
    "export_report": "EXPORT_REPORT",
}
_FIX_NODES = {
    "LOAD_FINDING",
    "CHECK_FIX_ELIGIBILITY",
    "PLAN_FIX",
    "GENERATE_PATCH",
    "VALIDATE_PATCH",
    "AWAIT_USER_CONFIRMATION",
    "APPLY_PATCH",
    "RUN_VALIDATION",
    "REINDEX_CHANGES",
    "RE_REVIEW",
    "FINALIZE",
}
_DIFF_HEADER = re.compile(r"^(---|\+\+\+) ([^\t]+)$")


class FixSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: UUID
    permission_mode: Literal["PROPOSE_ONLY", "APPLY_IN_ISOLATED_WORKSPACE"]


class FixActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_lock_version: int = Field(ge=0)


class FixPlanRequest(FixActionRequest):
    force_eligibility: bool = False


class FixHashActionRequest(FixActionRequest):
    patch_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class APIResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def normalize_datetimes(cls, value: object) -> object:
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class PatchProposalSummaryResponse(APIResponseModel):
    finding_id: UUID
    base_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    head_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    changed_files: list[str]
    estimated_changed_lines: int = Field(ge=1)
    rationale: str
    assumptions: list[str]
    validation_commands: list[ValidationCommand]
    residual_risks: list[str]
    confidence: float = Field(ge=0, le=1)
    patch_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    stale_at: datetime | None


class FixConfirmationResponse(APIResponseModel):
    id: UUID
    fix_session_id: UUID
    patch_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    expires_at: datetime
    confirmed_at: datetime | None
    consumed_at: datetime | None
    invalidated_at: datetime | None
    created_at: datetime


class ValidationRunResponse(APIResponseModel):
    id: UUID
    fix_session_id: UUID
    sequence: int = Field(ge=1)
    command: list[str]
    purpose: str
    required: bool
    status: ValidationStatus
    return_code: int | None
    stdout_summary: str | None
    stderr_summary: str | None
    output_truncated: bool
    error_code: str | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    created_at: datetime


class FixToolCallResponse(APIResponseModel):
    id: UUID
    fix_step_id: UUID
    tool_name: str
    permission: str
    arguments_summary: str
    output_summary: str | None
    status: str
    duration_ms: int | None
    error_code: str | None
    created_at: datetime


class FixStepResponse(APIResponseModel):
    id: UUID
    fix_session_id: UUID
    sequence: int = Field(ge=1)
    node: str
    status: str
    input_summary: str | None
    output_summary: str | None
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    created_at: datetime
    tool_calls: list[FixToolCallResponse]


class FixResultResponse(APIResponseModel):
    id: UUID
    fix_session_id: UUID
    resolution: FixResolution
    validation_status: ValidationStatus | None
    re_review_status: str
    residual_findings: list[str]
    residual_risks: list[str]
    report: PostFixReport
    created_at: datetime


class FixSessionResponse(APIResponseModel):
    id: UUID
    repository_id: UUID
    pull_request_id: UUID
    finding_id: UUID
    source_agent_run_id: UUID
    base_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    head_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    index_version_id: UUID | None
    workspace_index_version_id: UUID | None
    status: FixSessionStatus
    current_node: str | None
    permission_mode: FixPermissionMode
    workspace_path: str | None
    workspace_state_hash: str | None
    cleanup_status: Literal[
        "NOT_CREATED", "ACTIVE", "CLEANUP_PENDING", "DELETED", "CLEANUP_FAILED", "RETAINED"
    ]
    model_profile: str | None
    workflow_version: str | None
    eligibility: FixEligibilityResult | None
    allowed_actions: list[
        Literal[
            "PLAN",
            "GENERATE",
            "CONFIRM",
            "APPLY",
            "VALIDATE",
            "RE_REVIEW",
            "CANCEL",
            "ROLLBACK",
            "DELETE_WORKSPACE",
            "EXPORT_PATCH",
            "EXPORT_REPORT",
        ]
    ]
    lock_version: int = Field(ge=0)
    cancellation_requested: bool
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None
    last_active_at: datetime
    updated_at: datetime


class FixSessionDetailResponse(FixSessionResponse):
    plan: FixPlan | None
    proposal: PatchProposalSummaryResponse | None
    patch_inspection: PatchInspection | None
    confirmation: FixConfirmationResponse | None
    validation_plan: ValidationPlan | None
    validation_runs: list[ValidationRunResponse]
    steps: list[FixStepResponse]
    re_review: ReReviewAssessment | None
    result: FixResultResponse | None


class FixSessionListResponse(APIResponseModel):
    items: list[FixSessionResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class FixPatchFileResponse(APIResponseModel):
    path: str
    status: Literal["added", "modified", "deleted", "renamed"]


class FixPatchResponse(APIResponseModel):
    fix_session_id: UUID
    head_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    patch_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    unified_diff: str
    changed_files: list[FixPatchFileResponse]
    selected_path: str | None
    original: str | None
    modified: str | None


class FixWorkspaceResponse(APIResponseModel):
    fix_session_id: str
    repository_id: str
    path: str
    cleanup_status: Literal[
        "ACTIVE", "CLEANUP_PENDING", "CLEANUP_FAILED", "RETAINED", "ORPHANED"
    ]
    last_active_at: datetime
    expired: bool


class FixWorkspaceListResponse(APIResponseModel):
    items: list[FixWorkspaceResponse]
    total: int = Field(ge=0)
    retention_hours: int = Field(ge=1)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_session(request: Request):  # type: ignore[no-untyped-def]
    session = request.app.state.database.session_factory()
    try:
        yield session
    finally:
        session.close()


SessionDependency = Annotated[Session, Depends(get_session)]


def _manager(request: Request) -> FixManager:
    manager = getattr(request.app.state, "fix_manager", None)
    if manager is None:
        raise StudioAPIError(503, "fix_workflow_unavailable", "Autofix manager is unavailable.")
    return manager


async def _idempotent(
    request: Request,
    *,
    scope: str,
    payload: object,
    operation: Callable[[], Awaitable[T]],
) -> T:
    key = request.headers.get("Idempotency-Key")
    try:
        return await _manager(request).idempotency.execute(scope, key, payload, operation)
    except FixManagerError as exc:
        raise StudioAPIError(exc.status_code, exc.code, exc.message) from exc
    except AutofixError as exc:
        raise StudioAPIError(_autofix_status(exc.code), exc.code, str(exc)) from exc


def _autofix_status(code: str) -> int:
    if code in {"fix_session_not_found", "fix_finding_not_found"}:
        return 404
    if code in {"fix_patch_unsafe", "fix_validation_forbidden"}:
        return 422
    if code in {"fix_workspace_unavailable", "fix_workflow_unavailable"}:
        return 503
    return 409


def _get_fix_session(session: Session, session_id: str) -> FixSession:
    fix_session = session.get(FixSession, session_id)
    if fix_session is None:
        raise StudioAPIError(404, "fix_session_not_found", "Fix Session was not found.")
    return fix_session


def _latest_proposal(session: Session, session_id: str) -> PatchProposalRecord | None:
    return session.scalar(
        select(PatchProposalRecord)
        .where(PatchProposalRecord.fix_session_id == session_id)
        .order_by(PatchProposalRecord.proposal_version.desc())
        .limit(1)
    )


def _latest_confirmation(session: Session, session_id: str) -> FixConfirmation | None:
    return session.scalar(
        select(FixConfirmation)
        .where(FixConfirmation.fix_session_id == session_id)
        .order_by(FixConfirmation.created_at.desc())
        .limit(1)
    )


def _result(session: Session, session_id: str) -> FixResult | None:
    return session.scalar(select(FixResult).where(FixResult.fix_session_id == session_id).limit(1))


def _validation_runs(session: Session, session_id: str) -> list[ValidationRun]:
    return list(
        session.scalars(
            select(ValidationRun)
            .where(ValidationRun.fix_session_id == session_id)
            .order_by(ValidationRun.sequence)
        )
    )


def _is_confirmation_live(confirmation: FixConfirmation | None, fix_session: FixSession) -> bool:
    if confirmation is None:
        return False
    expires_at = confirmation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return bool(
        confirmation.confirmed_at is not None
        and confirmation.consumed_at is None
        and confirmation.invalidated_at is None
        and expires_at > utcnow()
        and confirmation.head_sha == fix_session.head_sha
    )


def _session_summary(
    session: Session,
    fix_session: FixSession,
    *,
    proposal: PatchProposalRecord | None = None,
    confirmation: FixConfirmation | None = None,
    result: FixResult | None = None,
) -> dict[str, Any]:
    proposal = proposal if proposal is not None else _latest_proposal(session, fix_session.id)
    confirmation = confirmation if confirmation is not None else _latest_confirmation(session, fix_session.id)
    result = result if result is not None else _result(session, fix_session.id)
    raw_actions = allowed_actions(
        fix_session.status,
        fix_session.permission_mode,
        has_workspace=bool(fix_session.workspace_path),
        has_patch=proposal is not None,
        has_result=result is not None,
    )
    if fix_session.status == "CREATED":
        raw_actions = ["plan", *[action for action in raw_actions if action != "plan"]]
    if fix_session.status in {
        "VALIDATION_COMPLETE",
        "REINDEXING_CHANGES",
        "RE_REVIEWING",
        "FINALIZING",
        "COMPLETED",
        "FAILED",
        "STALE",
        "CANCELLED",
        "ROLLED_BACK",
    }:
        raw_actions = [action for action in raw_actions if action != "cancel"]
    confirmation_live = _is_confirmation_live(confirmation, fix_session)
    if fix_session.status == "AWAITING_USER_CONFIRMATION":
        raw_actions = [action for action in raw_actions if action != "apply"]
        if confirmation_live:
            raw_actions = [action for action in raw_actions if action != "confirm"] + ["apply"]
    actions = [_ACTION_NAMES[action] for action in raw_actions if action in _ACTION_NAMES]
    eligibility = None
    if fix_session.eligibility_status is not None:
        eligibility = {
            "status": fix_session.eligibility_status,
            "reasons": fix_session.eligibility_reasons_json or [],
            "warnings": fix_session.eligibility_warnings_json or [],
            "force_allowed": fix_session.eligibility_status == "NEEDS_CONFIRMATION",
        }
    return {
        "id": fix_session.id,
        "repository_id": fix_session.repository_id,
        "pull_request_id": fix_session.pull_request_id,
        "finding_id": fix_session.finding_id,
        "source_agent_run_id": fix_session.source_agent_run_id,
        "base_sha": fix_session.base_sha,
        "head_sha": fix_session.head_sha,
        "index_version_id": fix_session.index_version_id,
        "workspace_index_version_id": fix_session.workspace_index_version_id,
        "status": fix_session.status,
        "current_node": fix_session.current_node,
        "permission_mode": fix_session.permission_mode,
        "workspace_path": fix_session.workspace_path,
        "workspace_state_hash": fix_session.workspace_state_hash,
        "cleanup_status": fix_session.cleanup_status,
        "model_profile": fix_session.model_profile,
        "workflow_version": fix_session.workflow_version,
        "eligibility": eligibility,
        "allowed_actions": list(dict.fromkeys(actions)),
        "lock_version": fix_session.lock_version,
        "cancellation_requested": fix_session.cancellation_requested,
        "input_tokens": fix_session.input_tokens,
        "output_tokens": fix_session.output_tokens,
        "latency_ms": fix_session.latency_ms,
        "retry_count": fix_session.retry_count,
        "created_at": fix_session.created_at,
        "started_at": fix_session.started_at,
        "finished_at": fix_session.finished_at,
        "error_code": fix_session.error_code,
        "error_message": fix_session.error_message,
        "last_active_at": fix_session.last_active_at,
        "updated_at": fix_session.updated_at,
    }


def _proposal_summary(
    proposal: PatchProposalRecord | None,
    finding_id: str,
) -> dict[str, Any] | None:
    if proposal is None:
        return None
    validation_plan = proposal.validation_plan_json or {}
    commands = []
    if isinstance(validation_plan, dict):
        commands = validation_plan.get("commands") or validation_plan.get("model_suggested_only") or []
    return {
        "finding_id": finding_id,
        "base_sha": proposal.base_sha,
        "head_sha": proposal.head_sha,
        "changed_files": proposal.changed_files_json or [],
        "estimated_changed_lines": proposal.changed_lines,
        "rationale": proposal.rationale,
        "assumptions": proposal.assumptions_json or [],
        "validation_commands": commands,
        "residual_risks": proposal.risk_notes_json or [],
        "confidence": proposal.confidence,
        "patch_hash": proposal.patch_hash,
        "created_at": proposal.created_at,
        "stale_at": proposal.stale_at,
    }
def _patch_counts(patch: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    in_hunk = False
    for line in patch.replace("\r\n", "\n").splitlines():
        if line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif in_hunk and line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return additions, deletions


def _patch_inspection(proposal: PatchProposalRecord | None) -> dict[str, Any] | None:
    if proposal is None:
        return None
    additions, deletions = _patch_counts(proposal.patch)
    return {
        "patch_hash": proposal.patch_hash,
        "changed_files": proposal.changed_files_json or [],
        "changed_lines": proposal.changed_lines,
        "additions": additions,
        "deletions": deletions,
        "warnings": proposal.risk_notes_json or [],
        "requires_confirmation": True,
    }


def _confirmation_payload(confirmation: FixConfirmation | None) -> dict[str, Any] | None:
    if confirmation is None:
        return None
    return {
        "id": confirmation.id,
        "fix_session_id": confirmation.fix_session_id,
        "patch_hash": confirmation.patch_hash,
        "expires_at": confirmation.expires_at,
        "confirmed_at": confirmation.confirmed_at,
        "consumed_at": confirmation.consumed_at,
        "invalidated_at": confirmation.invalidated_at,
        "created_at": confirmation.created_at,
    }


def _validation_run_payload(item: ValidationRun) -> dict[str, Any]:
    return {
        "id": item.id,
        "fix_session_id": item.fix_session_id,
        "sequence": item.sequence,
        "command": item.command,
        "purpose": item.purpose,
        "required": item.required,
        "status": item.status,
        "return_code": item.return_code,
        "stdout_summary": item.stdout_summary,
        "stderr_summary": item.stderr_summary,
        "output_truncated": item.output_truncated,
        "error_code": item.error_code,
        "started_at": item.started_at,
        "finished_at": item.finished_at,
        "duration_ms": item.duration_ms,
        "created_at": item.created_at,
    }


def _result_payload(result: FixResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "id": result.id,
        "fix_session_id": result.fix_session_id,
        "resolution": result.resolution,
        "validation_status": result.validation_status,
        "re_review_status": result.re_review_status,
        "residual_findings": result.residual_findings_json or [],
        "residual_risks": result.residual_risks_json or [],
        "report": _post_fix_report(result.report_json),
        "created_at": result.created_at,
    }


def _detail(session: Session, fix_session: FixSession) -> dict[str, Any]:
    proposal = _latest_proposal(session, fix_session.id)
    confirmation = _latest_confirmation(session, fix_session.id)
    result = _result(session, fix_session.id)
    validation_plan = _validation_plan_payload(proposal)
    re_review = session.scalar(
        select(FixEvent)
        .where(FixEvent.fix_session_id == fix_session.id, FixEvent.event_type == "re_review")
        .order_by(FixEvent.sequence.desc())
        .limit(1)
    )
    steps = list(
        session.scalars(
            select(FixStep)
            .where(FixStep.fix_session_id == fix_session.id)
            .order_by(FixStep.sequence)
        )
    )
    tool_calls_by_step: dict[str, list[FixToolCallRecord]] = {}
    if steps:
        for call in session.scalars(
            select(FixToolCallRecord)
            .where(FixToolCallRecord.fix_step_id.in_([step.id for step in steps]))
            .order_by(FixToolCallRecord.created_at)
        ):
            tool_calls_by_step.setdefault(call.fix_step_id, []).append(call)
    return {
        **_session_summary(
            session,
            fix_session,
            proposal=proposal,
            confirmation=confirmation,
            result=result,
        ),
        "plan": fix_session.plan_json,
        "proposal": _proposal_summary(proposal, fix_session.finding_id),
        "patch_inspection": _patch_inspection(proposal),
        "confirmation": _confirmation_payload(confirmation),
        "validation_plan": validation_plan,
        "validation_runs": [
            _validation_run_payload(item) for item in _validation_runs(session, fix_session.id)
        ],
        "steps": [
            {
                "id": step.id,
                "fix_session_id": step.fix_session_id,
                "sequence": step.sequence,
                "node": step.node,
                "status": step.status,
                "input_summary": step.input_summary,
                "output_summary": step.output_summary,
                "error_code": step.error_code,
                "error_message": step.error_message,
                "started_at": step.started_at,
                "finished_at": step.finished_at,
                "duration_ms": step.duration_ms,
                "created_at": step.created_at,
                "tool_calls": [
                    {
                        "id": call.id,
                        "fix_step_id": call.fix_step_id,
                        "tool_name": call.tool_name,
                        "permission": call.permission,
                        "arguments_summary": call.arguments_summary,
                        "output_summary": call.output_summary,
                        "status": call.status,
                        "duration_ms": call.duration_ms,
                        "error_code": call.error_code,
                        "created_at": call.created_at,
                    }
                    for call in tool_calls_by_step.get(step.id, [])
                ],
            }
            for step in steps
        ],
        "re_review": re_review.payload_json if re_review is not None else None,
        "result": _result_payload(result),
    }


def _validation_plan_payload(proposal: PatchProposalRecord | None) -> dict[str, Any] | None:
    if proposal is None:
        return None
    raw = proposal.validation_plan_json or {}
    if not isinstance(raw, dict):
        return {"commands": [], "notes": ["Persisted validation plan was invalid."]}
    if "commands" in raw:
        return {"commands": raw.get("commands") or [], "notes": raw.get("notes") or []}
    if raw.get("model_suggested_only"):
        return {
            "commands": [],
            "notes": [
                "Model-suggested commands are informational; the server derives an allowlisted plan before execution."
            ],
        }
    return {"commands": [], "notes": []}


def _post_fix_report(raw: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "fix_session_id",
        "finding_id",
        "patch_hash",
        "applied",
        "validation_status",
        "commands_run",
        "passed_commands",
        "failed_commands",
        "re_review_status",
        "finding_resolution",
        "residual_findings",
        "residual_risks",
        "final_summary",
    )
    candidate = {field: raw[field] for field in fields if field in raw}
    try:
        return PostFixReport.model_validate(candidate).model_dump(mode="json")
    except ValueError as exc:
        raise StudioAPIError(
            409,
            "fix_report_integrity_error",
            "Persisted Post-Fix Report failed schema verification.",
        ) from exc
def _read_detail(request: Request, session_id: str) -> dict[str, Any]:
    with request.app.state.database.session_factory() as session:
        return _detail(session, _get_fix_session(session, session_id))


@router.post("", response_model=FixSessionDetailResponse)
async def create_fix_session(
    body: FixSessionCreateRequest,
    request: Request,
) -> dict[str, Any]:
    payload = body.model_dump(mode="json")

    async def operation() -> dict[str, Any]:
        session_id = await _manager(request).initialize(
            finding_id=str(body.finding_id),
            permission_mode=body.permission_mode,
        )
        return _read_detail(request, session_id)

    return await _idempotent(request, scope="fix:create", payload=payload, operation=operation)


@router.get("", response_model=FixSessionListResponse)
def list_fix_sessions(
    session: SessionDependency,
    pull_request_id: UUID | None = None,
    finding_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    filters = []
    if pull_request_id is not None:
        filters.append(FixSession.pull_request_id == str(pull_request_id))
    if finding_id is not None:
        filters.append(FixSession.finding_id == str(finding_id))
    total = session.scalar(select(func.count()).select_from(FixSession).where(*filters)) or 0
    items = list(
        session.scalars(
            select(FixSession)
            .where(*filters)
            .order_by(FixSession.created_at.desc(), FixSession.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return {
        "items": [_session_summary(session, item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{session_id}", response_model=FixSessionDetailResponse)
def get_fix_session(session_id: UUID, session: SessionDependency) -> dict[str, Any]:
    return _detail(session, _get_fix_session(session, str(session_id)))


async def _action_response(
    request: Request,
    session_id: UUID,
    action: str,
    payload: dict[str, Any],
    operation: Callable[[], Awaitable[str]],
) -> dict[str, Any]:
    async def execute() -> dict[str, Any]:
        result_id = await operation()
        return _read_detail(request, result_id)

    return await _idempotent(
        request,
        scope=f"fix:{session_id}:{action}",
        payload=payload,
        operation=execute,
    )


@router.post("/{session_id}/plan", response_model=FixSessionDetailResponse)
async def plan_fix_session(
    session_id: UUID,
    body: FixPlanRequest,
    request: Request,
) -> dict[str, Any]:
    return await _action_response(
        request,
        session_id,
        "plan",
        body.model_dump(),
        lambda: _manager(request).plan(
            str(session_id),
            expected_lock_version=body.expected_lock_version,
            force_eligibility=body.force_eligibility,
        ),
    )


@router.post("/{session_id}/generate", response_model=FixSessionDetailResponse)
async def generate_fix_session(
    session_id: UUID,
    body: FixActionRequest,
    request: Request,
) -> dict[str, Any]:
    return await _action_response(
        request,
        session_id,
        "generate",
        body.model_dump(),
        lambda: _manager(request).generate(
            str(session_id), expected_lock_version=body.expected_lock_version
        ),
    )


@router.post("/{session_id}/confirm", response_model=FixSessionDetailResponse)
async def confirm_fix_session(
    session_id: UUID,
    body: FixHashActionRequest,
    request: Request,
) -> dict[str, Any]:
    return await _action_response(
        request,
        session_id,
        "confirm",
        body.model_dump(),
        lambda: _manager(request).confirm(
            str(session_id),
            expected_lock_version=body.expected_lock_version,
            patch_hash=body.patch_hash,
        ),
    )


@router.post("/{session_id}/apply", response_model=FixSessionDetailResponse)
async def apply_fix_session(
    session_id: UUID,
    body: FixHashActionRequest,
    request: Request,
) -> dict[str, Any]:
    return await _action_response(
        request,
        session_id,
        "apply",
        body.model_dump(),
        lambda: _manager(request).apply(
            str(session_id),
            expected_lock_version=body.expected_lock_version,
            patch_hash=body.patch_hash,
        ),
    )


@router.post("/{session_id}/validate", response_model=FixSessionDetailResponse)
async def validate_fix_session(
    session_id: UUID,
    body: FixActionRequest,
    request: Request,
) -> dict[str, Any]:
    return await _action_response(
        request,
        session_id,
        "validate",
        body.model_dump(),
        lambda: _manager(request).validate(
            str(session_id), expected_lock_version=body.expected_lock_version
        ),
    )


@router.post("/{session_id}/re-review", response_model=FixSessionDetailResponse)
async def re_review_fix_session(
    session_id: UUID,
    body: FixActionRequest,
    request: Request,
) -> dict[str, Any]:
    return await _action_response(
        request,
        session_id,
        "re-review",
        body.model_dump(),
        lambda: _manager(request).re_review(
            str(session_id), expected_lock_version=body.expected_lock_version
        ),
    )


@router.post("/{session_id}/cancel", response_model=FixSessionDetailResponse)
async def cancel_fix_session(
    session_id: UUID,
    body: FixActionRequest,
    request: Request,
) -> dict[str, Any]:
    return await _action_response(
        request,
        session_id,
        "cancel",
        body.model_dump(),
        lambda: _manager(request).cancel(
            str(session_id), expected_lock_version=body.expected_lock_version
        ),
    )


@router.post("/{session_id}/rollback", response_model=FixSessionDetailResponse)
async def rollback_fix_session(
    session_id: UUID,
    body: FixActionRequest,
    request: Request,
) -> dict[str, Any]:
    return await _action_response(
        request,
        session_id,
        "rollback",
        body.model_dump(),
        lambda: _manager(request).rollback(
            str(session_id), expected_lock_version=body.expected_lock_version
        ),
    )


@router.delete("/{session_id}/workspace", status_code=204)
async def delete_fix_workspace(
    session_id: UUID,
    body: FixActionRequest,
    request: Request,
) -> Response:
    async def operation() -> None:
        await _manager(request).delete_workspace(
            str(session_id), expected_lock_version=body.expected_lock_version
        )

    await _idempotent(
        request,
        scope=f"fix:{session_id}:delete-workspace",
        payload=body.model_dump(),
        operation=operation,
    )
    return Response(status_code=204)


def _patch_file_statuses(patch: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    previous: str | None = None
    for raw_line in patch.replace("\r\n", "\n").splitlines():
        match = _DIFF_HEADER.match(raw_line)
        if match is None:
            continue
        kind, raw_path = match.groups()
        path = _clean_diff_path(raw_path)
        if kind == "---":
            previous = path
            continue
        selected = path or previous
        if selected is None:
            continue
        status = "added" if previous is None else "deleted" if path is None else "modified"
        result.append({"path": selected, "status": status})
        previous = None
    return list({item["path"]: item for item in result}.values())


def _clean_diff_path(raw: str) -> str | None:
    if raw == "/dev/null":
        return None
    if raw.startswith(("a/", "b/")):
        raw = raw[2:]
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path.as_posix()


@router.get("/{session_id}/patch", response_model=FixPatchResponse)
def get_fix_patch(
    session_id: UUID,
    request: Request,
    session: SessionDependency,
    path: str | None = Query(default=None, min_length=1, max_length=4096),
    download: bool = False,
) -> Response | dict[str, Any]:
    fix_session = _get_fix_session(session, str(session_id))
    proposal = _latest_proposal(session, fix_session.id)
    if proposal is None:
        raise StudioAPIError(404, "fix_patch_not_found", "Patch Proposal was not found.")
    authoritative_hash = compute_patch_hash(proposal.patch)
    if authoritative_hash != proposal.patch_hash:
        raise StudioAPIError(409, "fix_patch_integrity_error", "Persisted Patch Hash verification failed.")
    if download:
        filename = f"tracegate-fix-{fix_session.id}-{proposal.patch_hash[:12]}.patch"
        return Response(
            proposal.patch,
            media_type="text/x-diff; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-TraceGate-Patch-Hash": proposal.patch_hash,
            },
        )
    files = _patch_file_statuses(proposal.patch)
    allowed_paths = {item["path"] for item in files}
    if path is not None and path not in allowed_paths:
        raise StudioAPIError(404, "fix_patch_path_not_found", "Selected Patch path was not found.")
    original: str | None = None
    modified: str | None = None
    if path is not None and fix_session.workspace_path:
        repository = session.get(Repository, fix_session.repository_id)
        if repository is not None and repository.local_path:
            try:
                workspace = request.app.state.fix_manager.workspace_manager.load(
                    session_id=fix_session.id,
                    repository_id=fix_session.repository_id,
                    source_root=Path(repository.local_path),
                    head_sha=fix_session.head_sha,
                )
                original, modified = request.app.state.fix_manager.workspace_manager.project_file_versions(
                    workspace, proposal.patch, path
                )
            except (AutofixError, OSError, RepositoryPathError):
                original = modified = None
    return {
        "fix_session_id": fix_session.id,
        "head_sha": fix_session.head_sha,
        "patch_hash": proposal.patch_hash,
        "unified_diff": proposal.patch,
        "changed_files": files,
        "selected_path": path,
        "original": original,
        "modified": modified,
    }


@router.get("/{session_id}/report", response_model=FixResultResponse)
def get_fix_report(
    session_id: UUID,
    session: SessionDependency,
    download: bool = False,
) -> Response | dict[str, Any]:
    _get_fix_session(session, str(session_id))
    result = _result(session, str(session_id))
    payload = _result_payload(result)
    if payload is None:
        raise StudioAPIError(404, "fix_report_not_found", "Post-Fix Report was not found.")
    if download:
        filename = f"tracegate-fix-{session_id}-report.json"
        report_fields = set(payload["report"])
        artifacts = {
            key: value for key, value in result.report_json.items() if key not in report_fields
        }
        download_payload = {**payload, "artifacts": artifacts}
        content = (
            json.dumps(download_payload, ensure_ascii=False, default=_json_default, indent=2)
            + "\n"
        )
        return Response(
            content,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return payload


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def _event_envelope(event: FixEvent, fix_session: FixSession, session: Session) -> dict[str, Any]:
    event_type = event.event_type
    data: object = event.payload_json or {}
    if event_type in {"session", "fix_session.created"}:
        event_type = "session"
        data = _session_summary(session, fix_session)
    elif event_type.startswith("fix_step."):
        phase = event_type.removeprefix("fix_step.")
        raw = event.payload_json or {}
        node = raw.get("node") or raw.get("current_node")
        event_type = "workflow_step"
        data = {
            "status": raw.get("status")
            if raw.get("status") in {status.value for status in FixSessionStatus}
            else fix_session.status,
            "current_node": node if phase == "started" and node in _FIX_NODES else None,
            "message": raw.get("message")
            or f"{node or 'Fix workflow step'} {phase.replace('_', ' ')}.",
        }
    elif event_type not in _EVENT_TYPES:
        event_type = "error"
        data = {
            "code": "fix_event_type_invalid",
            "message": "A persisted Fix event has an unsupported type.",
            "recoverable": False,
        }
    return {
        "event_id": event.id,
        "sequence": event.sequence,
        "fix_session_id": event.fix_session_id,
        "created_at": event.created_at,
        "type": event_type,
        "data": data,
    }


@router.get("/{session_id}/events")
async def fix_session_events(
    session_id: UUID,
    request: Request,
    session: SessionDependency,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    fix_session = _get_fix_session(session, str(session_id))
    last_sequence = 0
    if last_event_id:
        if last_event_id.isdecimal():
            last_sequence = int(last_event_id)
        else:
            cursor = session.scalar(
                select(FixEvent).where(
                    FixEvent.fix_session_id == fix_session.id,
                    FixEvent.id == last_event_id,
                )
            )
            if cursor is None:
                raise StudioAPIError(
                    409,
                    "fix_event_cursor_invalid",
                    "Last-Event-ID does not belong to this Fix Session.",
                )
            last_sequence = cursor.sequence
    session_factory = request.app.state.database.session_factory

    async def stream() -> AsyncIterator[str]:
        cursor_sequence = last_sequence
        while True:
            if await request.is_disconnected():
                return
            with session_factory() as event_session:
                current = event_session.get(FixSession, str(session_id))
                if current is None:
                    envelope = {
                        "event_id": f"{session_id}:missing",
                        "sequence": max(cursor_sequence + 1, 1),
                        "fix_session_id": str(session_id),
                        "created_at": utcnow(),
                        "type": "error",
                        "data": {
                            "code": "fix_session_not_found",
                            "message": "Fix Session was not found.",
                            "recoverable": False,
                        },
                    }
                    yield _format_sse(envelope)
                    return
                events = list(
                    event_session.scalars(
                        select(FixEvent)
                        .where(
                            FixEvent.fix_session_id == current.id,
                            FixEvent.sequence > cursor_sequence,
                        )
                        .order_by(FixEvent.sequence)
                        .limit(200)
                    )
                )
                for event in events:
                    cursor_sequence = event.sequence
                    yield _format_sse(_event_envelope(event, current, event_session))
                if current.status in _TERMINAL and not events:
                    return
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _format_sse(envelope: dict[str, Any]) -> str:
    payload = json.dumps(envelope, ensure_ascii=False, default=_json_default, separators=(",", ":"))
    return f"id: {envelope['event_id']}\nevent: {envelope['type']}\ndata: {payload}\n\n"


@workspace_router.get("/fix-workspaces", response_model=FixWorkspaceListResponse)
def list_fix_workspaces(request: Request, session: SessionDependency) -> dict[str, Any]:
    """Report only worktrees beneath the managed Autofix root for diagnostics."""
    manager = _manager(request)
    managed_root = manager.workspace_manager.root.resolve(strict=False)
    settings = session.get(AppSettings, 1)
    retention_hours = settings.autofix_workspace_retention_hours if settings is not None else 24
    expires_before = utcnow() - timedelta(hours=retention_hours)
    records = list(
        session.scalars(
            select(FixSession)
            .where(
                FixSession.workspace_path.is_not(None),
                FixSession.cleanup_status.in_(["ACTIVE", "CLEANUP_PENDING", "CLEANUP_FAILED", "RETAINED"]),
            )
            .order_by(FixSession.last_active_at)
        )
    )
    items: list[dict[str, Any]] = []
    known_paths: set[Path] = set()
    for item in records:
        path = Path(item.workspace_path or "").expanduser().resolve(strict=False)
        if path == managed_root or not path.is_relative_to(managed_root):
            continue
        known_paths.add(path)
        last_active = item.last_active_at
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)
        items.append(
            {
                "fix_session_id": item.id,
                "repository_id": item.repository_id,
                "path": str(path),
                "cleanup_status": item.cleanup_status,
                "last_active_at": item.last_active_at,
                "expired": last_active < expires_before,
            }
        )
    for path in manager.workspace_manager.discover_residual_worktrees():
        resolved = path.resolve(strict=False)
        if resolved in known_paths:
            continue
        relative = resolved.relative_to(managed_root)
        if len(relative.parts) != 3 or relative.parts[-1] != "worktree":
            continue
        if not all(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", identifier)
            for identifier in relative.parts[:2]
        ):
            continue
        modified = datetime.fromtimestamp(resolved.stat().st_mtime, tz=timezone.utc)
        items.append(
            {
                "fix_session_id": relative.parts[1],
                "repository_id": relative.parts[0],
                "path": str(resolved),
                "cleanup_status": "ORPHANED",
                "last_active_at": modified,
                "expired": modified < expires_before,
            }
        )
    return {
        "items": items,
        "total": len(items),
        "retention_hours": retention_hours,
    }


@workspace_router.delete("/fix-workspaces/{session_id}", status_code=204)
async def cleanup_fix_workspace(session_id: str, request: Request) -> Response:
    """Clean exactly one residual workspace beneath the managed Autofix root."""

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", session_id):
        raise StudioAPIError(
            422,
            "fix_workspace_identifier_invalid",
            "Fix workspace session identifier is invalid.",
        )

    async def operation() -> None:
        await _manager(request).cleanup_diagnostic_workspace(session_id)

    await _idempotent(
        request,
        scope=f"fix-workspace:{session_id}:cleanup",
        payload={"session_id": session_id},
        operation=operation,
    )
    return Response(status_code=204)
