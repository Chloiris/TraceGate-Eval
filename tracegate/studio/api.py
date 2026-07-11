from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import re
import time
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import StudioSettings
from .errors import StudioAPIError
from .eval_bridge import EvalArtifactError, eval_component_status, evaluation_summary
from .github_sync import sync_repository_pull_requests
from .index_store import RepositoryIndexError, load_repository_map, persist_repository_index
from .models import (
    AgentRun,
    AgentStep,
    AppSettings,
    ChangedFileRecord,
    ChangedHunkRecord,
    CheckRunRecord,
    CommitRecord,
    EvidenceRecord,
    Finding,
    GraphEdgeRecord,
    IndexedFile,
    IndexedSymbol,
    IndexVersion,
    NotificationRecord,
    OnboardingState,
    PullRequest,
    Repository,
    RepositorySync,
    ToolCallRecord,
)
from .run_manager import configured_model, enqueue_analysis_run
from .schemas import (
    ComponentStatus,
    ConnectionTestRequest,
    ConnectionTestResponse,
    AgentRunListResponse,
    AgentRunResponse,
    AgentRunDetailResponse,
    AgentStepResponse,
    AnalyzeResponse,
    EvidenceResponse,
    EvaluationSummaryResponse,
    FindingResponse,
    HealthResponse,
    OnboardingResponse,
    OnboardingUpdate,
    NotificationCreate,
    NotificationResponse,
    IndexVersionResponse,
    PullRequestDiffResponse,
    ReviewMapResponse,
    ChangeTourResponse,
    CheckRunListResponse,
    ChangedFileDetailResponse,
    CommitResponse,
    PullRequestListResponse,
    PullRequestResponse,
    RepositoryCreate,
    RepositoryGraphResponse,
    RepositoryListResponse,
    RepositoryResponse,
    RepositorySyncResponse,
    RepositorySummaryResponse,
    RetrievalResponse,
    RepositoryUpdate,
    SettingsResponse,
    SettingsUpdate,
    SystemComponents,
    SystemStatusResponse,
    AgentDescriptorResponse,
    ToolDescriptorResponse,
    RegistryToggleRequest,
    DiagnosticsResponse,
    AgentEvidenceGraphResponse,
    UpdateStatusResponse,
)
from .security import require_local_token
from tracegate.github import GitHubAPIError, GitHubProvider
from tracegate.graph import symbol_node_id
from tracegate.indexing import changed_line_numbers
from tracegate.repository import RepositoryBoundary, RepositoryPathError
from tracegate.retrieval import hybrid_retrieve
from tracegate.models import ModelConfigurationError, ModelProviderError
from tracegate.agent.workflow import NODE_NAMES, WORKFLOW_VERSION
from tracegate.tools import create_read_only_registry
from tracegate.vcs import GitCommandError, GitProvider
from .config import default_data_dir


router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_local_token)])


class _ConnectionProbe(BaseModel):
    ok: Literal[True]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_session(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.database.session_factory()
    try:
        yield session
    finally:
        session.close()


SessionDependency = Annotated[Session, Depends(get_session)]


def _settings_row(session: Session) -> AppSettings:
    row = session.get(AppSettings, 1)
    if row is None:
        raise StudioAPIError(
            503,
            "settings_not_initialized",
            "Studio settings are missing; run the database migration before starting the API.",
        )
    return row


def _onboarding_row(session: Session) -> OnboardingState:
    row = session.get(OnboardingState, 1)
    if row is None:
        raise StudioAPIError(
            503,
            "onboarding_not_initialized",
            "Onboarding state is missing; run the database migration before starting the API.",
        )
    return row


def _github_status(settings: StudioSettings) -> ComponentStatus:
    if not settings.github_token_configured:
        return ComponentStatus(
            state="not_configured",
            configured=False,
            message="GitHub 尚未连接",
            detail="Configure a GitHub credential before accessing private repositories or monitoring PRs.",
        )
    return ComponentStatus(
        state="ready",
        configured=True,
        message="GitHub credentials are configured.",
        detail="The credential has not yet been verified by a GitHub connection test.",
    )


def _model_status(settings: StudioSettings, app_settings: AppSettings) -> ComponentStatus:
    has_model_configuration = bool(app_settings.model_provider and app_settings.model_name)
    if not settings.model_api_key_configured or not has_model_configuration:
        missing = []
        if not settings.model_api_key_configured:
            missing.append("credential")
        if not has_model_configuration:
            missing.append("provider/model")
        return ComponentStatus(
            state="not_configured",
            configured=False,
            message="模型尚未配置",
            detail="Missing " + " and ".join(missing) + "; no substitute provider was used.",
        )
    return ComponentStatus(
        state="ready",
        configured=True,
        message="Model settings and credentials are configured.",
        detail="The provider connection has not yet been verified.",
    )


def _database_status() -> ComponentStatus:
    return ComponentStatus(
        state="ready",
        configured=True,
        message="Database is connected and migrated.",
    )


def _webhook_relay_status(app_settings: AppSettings, snapshot: object) -> ComponentStatus:
    if not app_settings.webhook_relay_url or not app_settings.webhook_relay_device_id:
        return ComponentStatus(
            state="not_configured",
            configured=False,
            message="Webhook Relay 未配置",
            detail="Local ETag polling remains available without a public Relay.",
        )
    if not os.environ.get("TRACEGATE_RELAY_DEVICE_TOKEN"):
        return ComponentStatus(
            state="not_configured",
            configured=False,
            message="Webhook Relay 未配置",
            detail="Pair this device and restart the Sidecar so it can read the secure Relay token.",
        )
    connected = bool(getattr(snapshot, "connected", False))
    last_error = getattr(snapshot, "last_error", None)
    if connected:
        return ComponentStatus(
            state="ready",
            configured=True,
            message="Webhook Relay SSE is connected.",
            detail=f"Paired device: {app_settings.webhook_relay_device_id}",
        )
    return ComponentStatus(
        state="error" if last_error else "unavailable",
        configured=True,
        message="Webhook Relay connection is unavailable.",
        detail=last_error or "The authenticated SSE consumer is starting or reconnecting.",
    )


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    request.app.state.database.check_connection()
    return HealthResponse(
        status="ok",
        version=request.app.state.settings.version,
        database=_database_status(),
    )


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status(request: Request, session: SessionDependency) -> SystemStatusResponse:
    settings: StudioSettings = request.app.state.settings
    request.app.state.database.check_connection()
    app_settings = _settings_row(session)
    github = _github_status(settings)
    model = _model_status(settings, app_settings)
    relay_snapshot = request.app.state.relay_monitor.snapshot()
    webhook_relay = _webhook_relay_status(app_settings, relay_snapshot)
    eval_status = eval_component_status(settings.eval_root)
    components = SystemComponents(
        api=ComponentStatus(
            state="ready",
            configured=True,
            message="TraceGate Studio API is ready.",
            detail="Bearer authentication is enabled for every v1 endpoint.",
        ),
        database=_database_status(),
        github=github,
        model=model,
        webhook_relay=webhook_relay,
        eval=eval_status,
    )
    states = [component.state for component in components.__dict__.values()]
    status = "error" if "error" in states else "degraded" if any(
        state in {"not_configured", "unavailable"} for state in states
    ) else "ready"
    return SystemStatusResponse(status=status, components=components, checked_at=utcnow())


@router.post("/connections/test", response_model=ConnectionTestResponse)
async def test_connection(
    payload: ConnectionTestRequest,
    request: Request,
    session: SessionDependency,
) -> ConnectionTestResponse:
    started = time.monotonic()
    if payload.component == "backend":
        request.app.state.database.check_connection()
        return ConnectionTestResponse(
            component="backend",
            message="Authenticated local API and database connection succeeded.",
            detail="The probe used the current authenticated process and live database connection.",
            latency_ms=int((time.monotonic() - started) * 1000),
        )
    if payload.component == "github":
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise StudioAPIError(
                409,
                "github_not_configured",
                "GitHub 尚未连接; store a credential and restart the Sidecar before testing.",
            )
        provider = GitHubProvider(token=token)
        try:
            login, rate_limit = await provider.test_authenticated_connection()
        except GitHubAPIError as exc:
            raise StudioAPIError(
                502,
                "github_connection_failed",
                f"GitHub connection test failed: {exc}",
            ) from exc
        finally:
            await provider.close()
        return ConnectionTestResponse(
            component="github",
            message=f"GitHub authenticated as {login}.",
            detail=(
                f"REST rate limit remaining: {rate_limit.remaining}"
                if rate_limit.remaining is not None
                else "GitHub did not return a rate-limit remainder."
            ),
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    try:
        model = configured_model(session)
        result = await model.complete_structured(
            system_prompt="You are a connection probe. Return the required JSON and no additional claims.",
            user_prompt='Return exactly {"ok": true}.',
            output_schema=_ConnectionProbe,
        )
    except ModelConfigurationError as exc:
        raise StudioAPIError(409, "model_not_configured", f"Model connection test failed: {exc}") from exc
    except ModelProviderError as exc:
        raise StudioAPIError(502, "model_connection_failed", f"Model connection test failed: {exc}") from exc
    return ConnectionTestResponse(
        component="model",
        message=f"Model connection succeeded with {model.profile}.",
        detail=f"Provider mode: {result.provider_mode}; tokens: {result.input_tokens + result.output_tokens}.",
        latency_ms=int((time.monotonic() - started) * 1000),
    )


@router.get("/evaluations", response_model=EvaluationSummaryResponse)
def evaluations(request: Request) -> EvaluationSummaryResponse:
    try:
        payload = evaluation_summary(request.app.state.settings.eval_root)
    except EvalArtifactError as exc:
        raise StudioAPIError(409, "evaluation_artifacts_unavailable", str(exc)) from exc
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise StudioAPIError(
            409,
            "evaluation_artifacts_invalid",
            f"Checked-in evaluation artifacts are invalid ({type(exc).__name__}); no replacement metrics were returned.",
        ) from exc
    try:
        return EvaluationSummaryResponse.model_validate(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise StudioAPIError(
            500,
            "evaluation_artifacts_invalid",
            "Checked-in evaluation artifacts failed schema validation; no replacement metrics were returned.",
        ) from exc


_AGENT_METADATA: dict[str, tuple[str, list[str], list[str]]] = {
    "Planner": (
        "Turns the PR review request into bounded retrieval and analysis objectives.",
        ["structured planning", "retrieval query design"],
        [],
    ),
    "Repository Retriever": (
        "Retrieves commit-bound code and repository context through controlled tools.",
        ["repository search", "bounded file context"],
        ["search_code", "read_file", "list_directory", "get_git_diff", "get_git_log"],
    ),
    "Context Resolver": (
        "Resolves current evidence against stale, unknown, or conflicting claims.",
        ["EvidencePacket", "ClaimBench status resolution", "commit binding"],
        ["read_file", "search_code"],
    ),
    "Code Analyst": (
        "Produces structured candidate findings from retrieved code evidence.",
        ["semantic code review", "structured findings"],
        ["read_file", "search_code", "get_git_diff"],
    ),
    "Risk Reviewer": (
        "Applies TraceGate risk and evidence policy to candidate findings.",
        ["risk classification", "evidence-aware judgment"],
        [],
    ),
    "Verifier": (
        "Verifies paths, line ranges, evidence identifiers, and the analyzed commit.",
        ["EvidencePacket verifier", "source validation", "commit validation"],
        ["read_file"],
    ),
    "Report Composer": (
        "Composes the final review summary without inventing unsupported evidence.",
        ["structured report", "recommended review order"],
        [],
    ),
}


@router.get("/agents", response_model=list[AgentDescriptorResponse])
def agents(session: SessionDependency) -> list[AgentDescriptorResponse]:
    disabled = set(_settings_row(session).disabled_agents_json)
    return [
        AgentDescriptorResponse(
            name=name,
            version=WORKFLOW_VERSION,
            responsibility=_AGENT_METADATA[name][0],
            status="disabled" if name in disabled else "enabled",
            capabilities=_AGENT_METADATA[name][1],
            allowed_tools=_AGENT_METADATA[name][2],
        )
        for name in NODE_NAMES
    ]


@router.put("/agents/{agent_name}", response_model=AgentDescriptorResponse)
def update_agent_registry(
    agent_name: str,
    payload: RegistryToggleRequest,
    session: SessionDependency,
) -> AgentDescriptorResponse:
    if agent_name not in _AGENT_METADATA or agent_name not in NODE_NAMES:
        raise StudioAPIError(404, "agent_not_found", "Agent is not registered in the production workflow.")
    settings = _settings_row(session)
    disabled = set(settings.disabled_agents_json)
    if payload.enabled:
        disabled.discard(agent_name)
    else:
        disabled.add(agent_name)
    settings.disabled_agents_json = sorted(disabled)
    settings.updated_at = utcnow()
    session.commit()
    return AgentDescriptorResponse(
        name=agent_name,
        version=WORKFLOW_VERSION,
        responsibility=_AGENT_METADATA[agent_name][0],
        status="enabled" if payload.enabled else "disabled",
        capabilities=_AGENT_METADATA[agent_name][1],
        allowed_tools=_AGENT_METADATA[agent_name][2],
    )


@router.get("/tools", response_model=list[ToolDescriptorResponse])
def tools(session: SessionDependency) -> list[ToolDescriptorResponse]:
    settings = _settings_row(session)
    descriptors = create_read_only_registry(set(settings.disabled_tools_json)).descriptors()
    rows: list[ToolDescriptorResponse] = []
    for descriptor in descriptors:
        recent_call_count = int(
            session.scalar(
                select(func.count()).select_from(ToolCallRecord).where(
                    ToolCallRecord.tool_name == descriptor.name
                )
            )
            or 0
        )
        recent_error_count = int(
            session.scalar(
                select(func.count()).select_from(ToolCallRecord).where(
                    ToolCallRecord.tool_name == descriptor.name,
                    ToolCallRecord.status == "failed",
                )
            )
            or 0
        )
        most_recent_error = session.scalar(
            select(ToolCallRecord.error_code)
            .where(
                ToolCallRecord.tool_name == descriptor.name,
                ToolCallRecord.status == "failed",
            )
            .order_by(ToolCallRecord.id.desc())
            .limit(1)
        )
        rows.append(
            ToolDescriptorResponse(
                name=descriptor.name,
                description=descriptor.description,
                permission=descriptor.permission.value,
                timeout_seconds=descriptor.timeout_seconds,
                max_output_bytes=descriptor.max_output_bytes,
                input_schema=descriptor.input_schema,
                enabled=descriptor.enabled and descriptor.permission.value != "WRITE_CONFIRMATION",
                recent_call_count=recent_call_count,
                recent_error_count=recent_error_count,
                most_recent_error=most_recent_error,
            )
        )
    return rows


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    session: SessionDependency,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[NotificationRecord]:
    return list(
        session.scalars(
            select(NotificationRecord)
            .order_by(NotificationRecord.attempted_at.desc())
            .limit(limit)
        )
    )


@router.post("/notifications", response_model=NotificationResponse, status_code=201)
def create_notification(
    payload: NotificationCreate,
    session: SessionDependency,
) -> NotificationRecord:
    for model, identifier, label in (
        (Repository, payload.repository_id, "repository"),
        (PullRequest, payload.pull_request_id, "pull_request"),
        (AgentRun, payload.agent_run_id, "agent_run"),
    ):
        if identifier is not None and session.get(model, identifier) is None:
            raise StudioAPIError(404, f"{label}_not_found", f"Notification {label} was not found.")
    record = NotificationRecord(**payload.model_dump(), attempted_at=utcnow())
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@router.put("/tools/{tool_name}", response_model=ToolDescriptorResponse)
def update_tool_registry(
    tool_name: str,
    payload: RegistryToggleRequest,
    session: SessionDependency,
) -> ToolDescriptorResponse:
    settings = _settings_row(session)
    descriptors = {item.name: item for item in create_read_only_registry().descriptors()}
    descriptor = descriptors.get(tool_name)
    if descriptor is None:
        raise StudioAPIError(404, "tool_not_found", "Tool is not registered in the production Registry.")
    if descriptor.permission.value == "WRITE_CONFIRMATION" and payload.enabled:
        raise StudioAPIError(
            409,
            "write_tool_requires_confirmation",
            "Write tools cannot be enabled globally; each use requires write mode and exact confirmation.",
        )
    disabled = set(settings.disabled_tools_json)
    if payload.enabled:
        disabled.discard(tool_name)
    else:
        disabled.add(tool_name)
    settings.disabled_tools_json = sorted(disabled)
    settings.updated_at = utcnow()
    session.commit()
    refreshed = next(item for item in tools(session) if item.name == tool_name)
    return refreshed


def _artifact_version(root: Path, relative_path: str, pattern: str) -> str | None:
    try:
        content = (root / relative_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = re.search(pattern, content, flags=re.MULTILINE)
    return match.group(1) if match else None


@router.get("/diagnostics", response_model=DiagnosticsResponse)
def diagnostics(request: Request, session: SessionDependency) -> DiagnosticsResponse:
    settings: StudioSettings = request.app.state.settings
    app_settings = _settings_row(session)
    git_commit: str | None = None
    try:
        git_commit = GitProvider(RepositoryBoundary(settings.eval_root)).head_sha()
    except (OSError, RepositoryPathError, GitCommandError):
        git_commit = None
    frontend_version = _artifact_version(
        settings.eval_root,
        "apps/web/package.json",
        r'^\s*"version"\s*:\s*"([^"]+)"',
    )
    desktop_version = _artifact_version(
        settings.eval_root,
        "apps/desktop/src-tauri/Cargo.toml",
        r'^version\s*=\s*"([^"]+)"',
    )
    rust_minimum = _artifact_version(
        settings.eval_root,
        "apps/desktop/src-tauri/Cargo.toml",
        r'^rust-version\s*=\s*"([^"]+)"',
    )
    rust_version_info = os.environ.get("TRACEGATE_RUST_VERSION_INFO") or (
        f"minimum toolchain {rust_minimum}" if rust_minimum else None
    )
    database_url = request.app.state.database.engine.url
    monitor = request.app.state.repository_monitor.snapshot()
    relay_monitor = request.app.state.relay_monitor.snapshot()
    workspaces = list(
        session.scalars(
            select(Repository.local_path)
            .where(Repository.local_path.is_not(None))
            .order_by(Repository.full_name)
        )
    )
    latest_sync = session.scalar(
        select(RepositorySync).order_by(RepositorySync.started_at.desc()).limit(1)
    )
    latest_index = session.scalar(
        select(IndexVersion).order_by(IndexVersion.created_at.desc()).limit(1)
    )
    latest_run = session.scalar(
        select(AgentRun).order_by(AgentRun.created_at.desc()).limit(1)
    )
    delivered_notifications = int(
        session.scalar(
            select(func.count()).select_from(NotificationRecord).where(
                NotificationRecord.status == "delivered"
            )
        )
        or 0
    )
    failed_notifications = int(
        session.scalar(
            select(func.count()).select_from(NotificationRecord).where(
                NotificationRecord.status == "failed"
            )
        )
        or 0
    )
    return DiagnosticsResponse(
        software_version=settings.version,
        git_commit=git_commit,
        operating_system=platform.system(),
        architecture=platform.machine(),
        python_version=platform.python_version(),
        frontend_version=frontend_version,
        desktop_version=desktop_version,
        rust_version_info=rust_version_info,
        log_level=logging.getLevelName(logging.getLogger().getEffectiveLevel()),
        database_type=database_url.get_backend_name(),
        database_path=(database_url.database if database_url.get_backend_name() == "sqlite" else None),
        log_path=str(default_data_dir() / "logs" / "tracegate-studio.jsonl"),
        workspace_paths=[path for path in workspaces if path],
        sidecar_pid=os.getpid(),
        api_port=settings.port,
        github=_github_status(settings),
        model=_model_status(settings, app_settings),
        webhook_relay=_webhook_relay_status(app_settings, relay_monitor),
        monitor=monitor.__dict__,
        relay_monitor=relay_monitor.__dict__,
        agent_queue=request.app.state.run_manager.active_count(),
        index_queue=0,
        last_github_api_request_count=(latest_sync.github_api_request_count if latest_sync else None),
        last_github_api_duration_ms=(latest_sync.github_api_duration_ms if latest_sync else None),
        last_index_duration_ms=(latest_index.index_duration_ms if latest_index else None),
        last_graph_duration_ms=(latest_index.graph_duration_ms if latest_index else None),
        last_retrieval_result_count=(latest_run.retrieval_hit_count if latest_run else None),
        last_model_latency_ms=(latest_run.latency_ms if latest_run else None),
        last_model_input_tokens=(latest_run.input_tokens if latest_run else None),
        last_model_output_tokens=(latest_run.output_tokens if latest_run else None),
        last_model_retry_count=(latest_run.retry_count if latest_run else None),
        delivered_notification_count=delivered_notifications,
        failed_notification_count=failed_notifications,
        telemetry_enabled=False,
    )


@router.get("/system/update", response_model=UpdateStatusResponse)
def update_status(request: Request) -> UpdateStatusResponse:
    return UpdateStatusResponse(
        current_version=request.app.state.settings.version,
        channel="stable",
        configured=False,
        update_available=False,
        latest_version=None,
        manifest_url=None,
        signature_verification=False,
        message="Automatic updates are not configured; no unsigned update was offered.",
    )


@router.get("/settings", response_model=SettingsResponse)
def get_settings(session: SessionDependency) -> AppSettings:
    return _settings_row(session)


@router.put("/settings", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate, request: Request, session: SessionDependency) -> AppSettings:
    row = _settings_row(session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.updated_at = utcnow()
    session.commit()
    session.refresh(row)
    if {"background_monitoring", "github_poll_interval_seconds"} & payload.model_fields_set:
        request.app.state.repository_monitor.wake()
    if {"webhook_relay_url", "webhook_relay_device_id"} & payload.model_fields_set:
        request.app.state.relay_monitor.wake()
    return row


def _onboarding_response(
    settings: StudioSettings,
    app_settings: AppSettings,
    onboarding: OnboardingState,
    repository_added: bool,
    relay_snapshot: object,
) -> OnboardingResponse:
    return OnboardingResponse(
        completed=onboarding.completed,
        current_step=onboarding.current_step,
        github=_github_status(settings),
        model=_model_status(settings, app_settings),
        webhook_relay=_webhook_relay_status(app_settings, relay_snapshot),
        repository_added=repository_added,
        background_monitoring=app_settings.background_monitoring,
        launch_at_startup=app_settings.launch_at_startup,
        completed_at=onboarding.completed_at,
        updated_at=onboarding.updated_at,
    )


@router.get("/onboarding", response_model=OnboardingResponse)
def get_onboarding(request: Request, session: SessionDependency) -> OnboardingResponse:
    app_settings = _settings_row(session)
    onboarding = _onboarding_row(session)
    repository_added = bool(session.scalar(select(func.count()).select_from(Repository)))
    return _onboarding_response(
        request.app.state.settings,
        app_settings,
        onboarding,
        repository_added,
        request.app.state.relay_monitor.snapshot(),
    )


@router.put("/onboarding", response_model=OnboardingResponse)
def update_onboarding(
    payload: OnboardingUpdate,
    request: Request,
    session: SessionDependency,
) -> OnboardingResponse:
    app_settings = _settings_row(session)
    onboarding = _onboarding_row(session)
    values = payload.model_dump(exclude_unset=True)
    if "background_monitoring" in values:
        app_settings.background_monitoring = values["background_monitoring"]
    if "launch_at_startup" in values:
        app_settings.launch_at_startup = values["launch_at_startup"]
    if "completed" in values:
        onboarding.completed = values["completed"]
        onboarding.completed_at = utcnow() if values["completed"] else None
        if values["completed"]:
            onboarding.current_step = "complete"
    if "current_step" in values:
        if onboarding.completed and values["current_step"] != "complete":
            raise StudioAPIError(
                409,
                "invalid_onboarding_transition",
                "A completed onboarding flow must remain on the complete step.",
            )
        onboarding.current_step = values["current_step"]
    now = utcnow()
    onboarding.updated_at = now
    app_settings.updated_at = now
    session.commit()
    session.refresh(onboarding)
    session.refresh(app_settings)
    if "background_monitoring" in values:
        request.app.state.repository_monitor.wake()
    repository_added = bool(session.scalar(select(func.count()).select_from(Repository)))
    return _onboarding_response(
        request.app.state.settings,
        app_settings,
        onboarding,
        repository_added,
        request.app.state.relay_monitor.snapshot(),
    )


@router.get("/repositories", response_model=RepositoryListResponse)
def list_repositories(
    session: SessionDependency,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> RepositoryListResponse:
    total = int(session.scalar(select(func.count()).select_from(Repository)) or 0)
    rows = list(
        session.scalars(
            select(Repository).order_by(Repository.created_at.desc()).limit(limit).offset(offset)
        )
    )
    return RepositoryListResponse(items=rows, total=total, limit=limit, offset=offset)


@router.post("/repositories", response_model=RepositoryResponse, status_code=201)
def create_repository(
    payload: RepositoryCreate,
    request: Request,
    session: SessionDependency,
) -> Repository:
    owner, name = payload.full_name.split("/", 1)
    local_path = _canonical_local_path(payload.local_path)
    repository = Repository(
        owner=owner,
        name=name,
        full_name=payload.full_name,
        clone_url=payload.clone_url or f"https://github.com/{payload.full_name}.git",
        local_path=local_path,
        default_branch=payload.default_branch,
        monitoring_enabled=payload.monitoring_enabled,
        connection_status=(
            "pending" if request.app.state.settings.github_token_configured else "not_connected"
        ),
    )
    session.add(repository)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise StudioAPIError(
            409,
            "repository_already_exists",
            f"Repository {payload.full_name} has already been added.",
        ) from exc
    session.refresh(repository)
    request.app.state.repository_monitor.wake()
    return repository


def _repository(session: Session, repository_id: str) -> Repository:
    repository = session.get(Repository, repository_id)
    if repository is None:
        raise StudioAPIError(404, "repository_not_found", "Repository was not found.")
    return repository


def _canonical_local_path(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(RepositoryBoundary(Path(value)).root)
    except (OSError, RepositoryPathError) as exc:
        raise StudioAPIError(
            422,
            "invalid_repository_workspace",
            "The local workspace must be an existing readable directory.",
        ) from exc


@router.get("/repositories/{repository_id}", response_model=RepositoryResponse)
def get_repository(repository_id: str, session: SessionDependency) -> Repository:
    return _repository(session, repository_id)


@router.get("/repositories/{repository_id}/summary", response_model=RepositorySummaryResponse)
def repository_summary(
    repository_id: str,
    session: SessionDependency,
) -> RepositorySummaryResponse:
    repository = _repository(session, repository_id)
    active_pull_requests = int(
        session.scalar(
            select(func.count()).select_from(PullRequest).where(
                PullRequest.repository_id == repository.id,
                PullRequest.state == "open",
            )
        )
        or 0
    )
    if not repository.current_index_version:
        return RepositorySummaryResponse(
            repository_id=repository.id,
            commit_sha=repository.current_commit_sha,
            index_version=None,
            file_count=0,
            directory_count=0,
            symbol_count=0,
            dependency_edge_count=0,
            language_counts={},
            active_pull_requests=active_pull_requests,
        )
    version = session.get(IndexVersion, repository.current_index_version)
    if version is None:
        raise StudioAPIError(
            409,
            "repository_index_unavailable",
            "The repository points to a missing Index Version.",
        )
    files = list(
        session.scalars(
            select(IndexedFile).where(IndexedFile.index_version_id == version.id)
        )
    )
    language_counts: dict[str, int] = {}
    directories: set[str] = set()
    for item in files:
        language_counts[item.language] = language_counts.get(item.language, 0) + 1
        parent = Path(item.path).parent.as_posix()
        if parent != ".":
            directories.add(parent)
    edge_count = int(
        session.scalar(
            select(func.count()).select_from(GraphEdgeRecord).where(
                GraphEdgeRecord.index_version_id == version.id
            )
        )
        or 0
    )
    return RepositorySummaryResponse(
        repository_id=repository.id,
        commit_sha=version.commit_sha,
        index_version=version.id,
        file_count=version.file_count,
        directory_count=len(directories),
        symbol_count=version.symbol_count,
        dependency_edge_count=edge_count,
        language_counts=language_counts,
        active_pull_requests=active_pull_requests,
    )


@router.delete("/repositories/{repository_id}/cache", status_code=204)
def clear_repository_cache(repository_id: str, session: SessionDependency) -> Response:
    repository = _repository(session, repository_id)
    session.execute(delete(IndexVersion).where(IndexVersion.repository_id == repository.id))
    repository.current_commit_sha = None
    repository.current_index_version = None
    repository.updated_at = utcnow()
    session.commit()
    return Response(status_code=204)


@router.put("/repositories/{repository_id}", response_model=RepositoryResponse)
def update_repository(
    repository_id: str,
    payload: RepositoryUpdate,
    request: Request,
    session: SessionDependency,
) -> Repository:
    repository = _repository(session, repository_id)
    values = payload.model_dump(exclude_unset=True)
    if "local_path" in values:
        values["local_path"] = _canonical_local_path(values["local_path"])
    for field, value in values.items():
        setattr(repository, field, value)
    repository.updated_at = utcnow()
    session.commit()
    session.refresh(repository)
    if "monitoring_enabled" in values:
        request.app.state.repository_monitor.wake()
    return repository


@router.delete("/repositories/{repository_id}", status_code=204)
def delete_repository(repository_id: str, session: SessionDependency) -> Response:
    repository = _repository(session, repository_id)
    session.delete(repository)
    session.commit()
    return Response(status_code=204)


@router.post("/repositories/{repository_id}/sync", response_model=RepositorySyncResponse)
async def sync_repository(repository_id: str, session: SessionDependency) -> RepositorySyncResponse:
    repository = _repository(session, repository_id)
    try:
        result = await sync_repository_pull_requests(session, repository)
    except GitHubAPIError as exc:
        status_code = 429 if exc.status_code == 429 else 502
        raise StudioAPIError(status_code, "github_sync_failed", str(exc)) from exc
    return RepositorySyncResponse(
        sync_id=result.record.id,
        status=result.status,  # type: ignore[arg-type]
        changed_pull_requests=result.changed_pull_requests,
        changed_check_runs=result.changed_check_runs,
        etag=result.record.etag,
        github_rate_remaining=repository.github_rate_remaining,
        finished_at=result.record.finished_at or utcnow(),
    )


@router.post("/repositories/{repository_id}/index", response_model=IndexVersionResponse)
def index_repository(repository_id: str, session: SessionDependency) -> IndexVersionResponse:
    repository = _repository(session, repository_id)
    try:
        version, _repository_map = persist_repository_index(session, repository)
    except RepositoryIndexError as exc:
        session.rollback()
        raise StudioAPIError(409, "repository_index_unavailable", str(exc)) from exc
    except Exception as exc:
        session.rollback()
        raise StudioAPIError(500, "repository_index_failed", "Repository indexing failed; no previous index was returned as current.") from exc
    return IndexVersionResponse.model_validate(version)


@router.get("/repositories/{repository_id}/graph", response_model=RepositoryGraphResponse)
def repository_graph(repository_id: str, session: SessionDependency) -> RepositoryGraphResponse:
    _repository(session, repository_id)
    try:
        repository_map = load_repository_map(session, repository_id)
    except RepositoryIndexError as exc:
        raise StudioAPIError(409, "repository_index_unavailable", str(exc)) from exc
    return RepositoryGraphResponse(
        repository_id=repository_map.repository_id,
        commit_sha=repository_map.commit_sha,
        index_version=repository_map.index_version,
        nodes=[node.__dict__ for node in repository_map.nodes],
        edges=[edge.__dict__ for edge in repository_map.edges if edge.confirmed],
    )


@router.get("/repositories/{repository_id}/search", response_model=RetrievalResponse)
def search_repository(
    repository_id: str,
    session: SessionDependency,
    query: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=30, ge=1, le=100),
) -> RetrievalResponse:
    _repository(session, repository_id)
    try:
        result = hybrid_retrieve(session, repository_id, query, limit=limit)
    except ValueError as exc:
        raise StudioAPIError(409, "repository_index_unavailable", str(exc)) from exc
    return RetrievalResponse(
        repository_id=result.repository_id,
        index_version=result.index_version,
        commit_sha=result.commit_sha,
        query=result.query,
        hits=[hit.__dict__ for hit in result.hits],
        vector_search_enabled=result.vector_search_enabled,
        vector_search_message=result.vector_search_message,
    )


@router.get("/pull-requests", response_model=PullRequestListResponse)
def list_pull_requests(
    session: SessionDependency,
    repository_id: str | None = None,
    state: str | None = None,
    analysis_status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PullRequestListResponse:
    filters = []
    if repository_id:
        filters.append(PullRequest.repository_id == repository_id)
    if state:
        filters.append(PullRequest.state == state)
    if analysis_status:
        filters.append(PullRequest.analysis_status == analysis_status)
    total = int(session.scalar(select(func.count()).select_from(PullRequest).where(*filters)) or 0)
    rows = list(
        session.scalars(
            select(PullRequest)
            .where(*filters)
            .order_by(PullRequest.updated_at_github.desc(), PullRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return PullRequestListResponse(items=rows, total=total, limit=limit, offset=offset)


@router.get("/pull-requests/{pull_request_id}", response_model=PullRequestResponse)
def get_pull_request(pull_request_id: str, session: SessionDependency) -> PullRequest:
    pull_request = session.get(PullRequest, pull_request_id)
    if pull_request is None:
        raise StudioAPIError(404, "pull_request_not_found", "Pull Request was not found.")
    return pull_request


@router.get("/pull-requests/{pull_request_id}/checks", response_model=CheckRunListResponse)
def get_pull_request_checks(
    pull_request_id: str,
    session: SessionDependency,
) -> CheckRunListResponse:
    pull_request = session.get(PullRequest, pull_request_id)
    if pull_request is None:
        raise StudioAPIError(404, "pull_request_not_found", "Pull Request was not found.")
    rows = list(
        session.scalars(
            select(CheckRunRecord)
            .where(CheckRunRecord.pull_request_id == pull_request.id)
            .order_by(CheckRunRecord.name, CheckRunRecord.github_id)
        )
    )
    return CheckRunListResponse(
        items=rows,
        aggregate_status=pull_request.checks_status,  # type: ignore[arg-type]
        synced_at=pull_request.last_checks_synced_at,
    )


@router.get("/pull-requests/{pull_request_id}/commits", response_model=list[CommitResponse])
def get_pull_request_commits(
    pull_request_id: str,
    session: SessionDependency,
) -> list[CommitRecord]:
    pull_request = session.get(PullRequest, pull_request_id)
    if pull_request is None:
        raise StudioAPIError(404, "pull_request_not_found", "Pull Request was not found.")
    return list(
        session.scalars(
            select(CommitRecord)
            .where(CommitRecord.pull_request_id == pull_request.id)
            .order_by(CommitRecord.position)
        )
    )


@router.get("/pull-requests/{pull_request_id}/files", response_model=list[ChangedFileDetailResponse])
def get_pull_request_files(
    pull_request_id: str,
    session: SessionDependency,
) -> list[ChangedFileDetailResponse]:
    pull_request = session.get(PullRequest, pull_request_id)
    if pull_request is None:
        raise StudioAPIError(404, "pull_request_not_found", "Pull Request was not found.")
    if not pull_request.head_sha:
        raise StudioAPIError(
            409,
            "pull_request_head_missing",
            "Pull Request changed files require a synchronized Head SHA.",
        )
    rows = list(
        session.scalars(
            select(ChangedFileRecord)
            .where(
                ChangedFileRecord.pull_request_id == pull_request.id,
                ChangedFileRecord.head_sha == pull_request.head_sha,
            )
            .order_by(ChangedFileRecord.path)
        )
    )
    result: list[ChangedFileDetailResponse] = []
    for row in rows:
        hunks = list(
            session.scalars(
                select(ChangedHunkRecord)
                .where(ChangedHunkRecord.changed_file_id == row.id)
                .order_by(ChangedHunkRecord.sequence)
            )
        )
        result.append(
            ChangedFileDetailResponse.model_validate(
                {
                    **{field: getattr(row, field) for field in ChangedFileDetailResponse.model_fields if field != "hunks"},
                    "hunks": hunks,
                }
            )
        )
    return result


@router.get("/pull-requests/{pull_request_id}/diff", response_model=PullRequestDiffResponse)
def get_pull_request_diff(
    pull_request_id: str,
    session: SessionDependency,
    path: str | None = Query(default=None, max_length=2048),
) -> PullRequestDiffResponse:
    pull_request = session.get(PullRequest, pull_request_id)
    if pull_request is None:
        raise StudioAPIError(404, "pull_request_not_found", "Pull Request was not found.")
    repository = _repository(session, pull_request.repository_id)
    if not repository.local_path or not pull_request.base_sha or not pull_request.head_sha:
        raise StudioAPIError(409, "pull_request_diff_unavailable", "A local workspace and Base/Head SHAs are required.")
    try:
        boundary = RepositoryBoundary(Path(repository.local_path))
        git = GitProvider(boundary)
        names = git.run("diff", "--name-status", "--find-renames", f"{pull_request.base_sha}...{pull_request.head_sha}")
        unified = git.diff(pull_request.base_sha, pull_request.head_sha).stdout
    except (OSError, RepositoryPathError, GitCommandError) as exc:
        raise StudioAPIError(409, "pull_request_diff_unavailable", str(exc)) from exc
    changed_files = []
    for line in names.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            changed_files.append({"status": parts[0], "path": parts[-1]})
    selected_path = path or (changed_files[0]["path"] if changed_files else None)
    original: str | None = None
    modified: str | None = None
    if selected_path:
        if selected_path not in {item["path"] for item in changed_files}:
            raise StudioAPIError(422, "invalid_diff_path", "Selected path is not changed by this Pull Request.")
        try:
            original = git.show(pull_request.base_sha, selected_path).stdout
        except GitCommandError:
            original = None
        try:
            modified = git.show(pull_request.head_sha, selected_path).stdout
        except GitCommandError:
            modified = None
    return PullRequestDiffResponse(
        pull_request_id=pull_request.id,
        base_sha=pull_request.base_sha,
        head_sha=pull_request.head_sha,
        changed_files=changed_files,
        selected_path=selected_path,
        original=original,
        modified=modified,
        unified_diff=unified,
    )


def _change_status(raw_status: str) -> str:
    marker = raw_status[:1].upper()
    return {
        "A": "added",
        "D": "deleted",
        "R": "renamed",
    }.get(marker, "modified")


def _review_map(
    pull_request_id: str,
    session: Session,
) -> ReviewMapResponse:
    pull_request = session.get(PullRequest, pull_request_id)
    if pull_request is None:
        raise StudioAPIError(404, "pull_request_not_found", "Pull Request was not found.")
    repository = _repository(session, pull_request.repository_id)
    if not pull_request.head_sha or repository.current_commit_sha != pull_request.head_sha:
        raise StudioAPIError(
            409,
            "pull_request_index_mismatch",
            "Index the Pull Request Head SHA before requesting its Review Map.",
        )
    diff = get_pull_request_diff(pull_request_id, session, path=None)
    try:
        repository_map = load_repository_map(session, repository.id)
    except RepositoryIndexError as exc:
        raise StudioAPIError(409, "repository_index_unavailable", str(exc)) from exc
    if repository_map.commit_sha != pull_request.head_sha:
        raise StudioAPIError(
            409,
            "pull_request_index_mismatch",
            "The current static graph is not bound to this Pull Request Head SHA.",
        )

    changed = {item.path: _change_status(item.status) for item in diff.changed_files}
    node_by_id = {node.id: node for node in repository_map.nodes}
    changed_lines = changed_line_numbers(diff.unified_diff)
    changed_symbol_ids: set[str] = set()
    symbol_rows = session.execute(
        select(IndexedSymbol, IndexedFile)
        .join(IndexedFile, IndexedFile.id == IndexedSymbol.indexed_file_id)
        .where(IndexedFile.index_version_id == repository_map.index_version)
    ).all()
    for symbol, indexed_file in symbol_rows:
        lines = changed_lines.get(indexed_file.path, frozenset())
        if any(symbol.start_line <= line <= symbol.end_line for line in lines):
            changed_symbol_ids.add(
                symbol_node_id(indexed_file.path, symbol.qualified_name, symbol.start_line)
            )
    direct = {
        node.id
        for node in repository_map.nodes
        if node.path in changed and node.kind in {"file", "test"}
    } | changed_symbol_ids
    adjacency: dict[str, set[str]] = {node.id: set() for node in repository_map.nodes}
    for edge in repository_map.edges:
        if edge.confirmed and edge.source in adjacency and edge.target in adjacency:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)

    depth_by_id = {node_id: 0 for node_id in direct}
    frontier = set(direct)
    for depth in (1, 2):
        next_frontier: set[str] = set()
        for node_id in frontier:
            for neighbor in adjacency.get(node_id, set()):
                if neighbor not in depth_by_id:
                    depth_by_id[neighbor] = depth
                    next_frontier.add(neighbor)
        frontier = next_frontier

    run_ids = list(
        session.scalars(
            select(AgentRun.id).where(
                AgentRun.pull_request_id == pull_request.id,
                AgentRun.head_sha == pull_request.head_sha,
            )
        )
    )
    findings = (
        list(session.scalars(select(Finding).where(Finding.agent_run_id.in_(run_ids))))
        if run_ids
        else []
    )
    evidence = (
        list(session.scalars(select(EvidenceRecord).where(EvidenceRecord.agent_run_id.in_(run_ids))))
        if run_ids
        else []
    )
    finding_ids_by_path: dict[str, list[str]] = {}
    evidence_ids_by_path: dict[str, list[str]] = {}
    risk_by_path: dict[str, str] = {}
    risk_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    for finding in findings:
        if not finding.file_path:
            continue
        finding_ids_by_path.setdefault(finding.file_path, []).append(finding.id)
        current = risk_by_path.get(finding.file_path)
        if current is None or risk_order.get(finding.severity, -1) > risk_order.get(current, -1):
            risk_by_path[finding.file_path] = finding.severity
        for evidence_id in finding.evidence_ids_json:
            evidence_ids_by_path.setdefault(finding.file_path, []).append(evidence_id)
    for record in evidence:
        if record.file_path:
            evidence_ids_by_path.setdefault(record.file_path, []).append(record.id)

    nodes: list[dict[str, object]] = []
    selected_ids = set(depth_by_id)
    for node_id in sorted(selected_ids, key=lambda item: (depth_by_id[item], node_by_id[item].path, item)):
        node = node_by_id[node_id]
        nodes.append(
            {
                "id": node.id,
                "kind": node.kind,
                "label": node.label,
                "path": node.path,
                "symbol": node.symbol,
                "language": node.language,
                "impact_depth": depth_by_id[node.id],
                "change_status": changed.get(node.path),
                "risk": risk_by_path.get(node.path),
                "finding_ids": sorted(set(finding_ids_by_path.get(node.path, []))),
                "evidence_ids": sorted(set(evidence_ids_by_path.get(node.path, []))),
            }
        )

    represented_paths = {node_by_id[node_id].path for node_id in direct}
    for path, status in sorted(changed.items()):
        if path not in represented_paths:
            nodes.append(
                {
                    "id": f"diff:{path}",
                    "kind": "file",
                    "label": path.rsplit("/", 1)[-1],
                    "path": path,
                    "symbol": None,
                    "language": None,
                    "impact_depth": 0,
                    "change_status": status,
                    "risk": risk_by_path.get(path),
                    "finding_ids": sorted(set(finding_ids_by_path.get(path, []))),
                    "evidence_ids": sorted(set(evidence_ids_by_path.get(path, []))),
                }
            )

    edges: list[dict[str, object]] = [
        {
            "id": edge.id,
            "source": edge.source,
            "target": edge.target,
            "kind": edge.kind,
            "confirmed": edge.confirmed,
        }
        for edge in repository_map.edges
        if edge.confirmed and edge.source in selected_ids and edge.target in selected_ids
    ]

    path_target = {
        node["path"]: node["id"]
        for node in nodes
        if node["kind"] == "file" and isinstance(node["path"], str)
    }
    for finding in findings:
        if not finding.file_path or finding.file_path not in path_target:
            continue
        finding_node_id = f"finding:{finding.id}"
        nodes.append(
            {
                "id": finding_node_id,
                "kind": "finding",
                "label": finding.title,
                "path": finding.file_path,
                "symbol": finding.symbol,
                "language": None,
                "impact_depth": 0,
                "change_status": changed.get(finding.file_path),
                "risk": finding.severity,
                "finding_ids": [finding.id],
                "evidence_ids": finding.evidence_ids_json,
            }
        )
        edges.append(
            {
                "id": f"finding-edge:{finding.id}",
                "source": finding_node_id,
                "target": path_target[finding.file_path],
                "kind": "supported-by-code",
                "confirmed": finding.verifier_status == "verified",
            }
        )
    finding_node_ids = {node["id"] for node in nodes if node["kind"] == "finding"}
    for record in evidence:
        related = [
            finding
            for finding in findings
            if record.id in finding.evidence_ids_json and f"finding:{finding.id}" in finding_node_ids
        ]
        if not related:
            continue
        evidence_node_id = f"evidence:{record.id}"
        nodes.append(
            {
                "id": evidence_node_id,
                "kind": "evidence",
                "label": record.source_type,
                "path": record.file_path,
                "symbol": None,
                "language": None,
                "impact_depth": 0,
                "change_status": changed.get(record.file_path or ""),
                "risk": None,
                "finding_ids": [finding.id for finding in related],
                "evidence_ids": [record.id],
            }
        )
        for finding in related:
            edges.append(
                {
                    "id": f"evidence-edge:{record.id}:{finding.id}",
                    "source": evidence_node_id,
                    "target": f"finding:{finding.id}",
                    "kind": "supports",
                    "confirmed": True,
                }
            )

    node_limit = 800
    truncated = len(nodes) > node_limit
    if truncated:
        nodes = nodes[:node_limit]
        retained = {str(node["id"]) for node in nodes}
        edges = [edge for edge in edges if edge["source"] in retained and edge["target"] in retained]
    return ReviewMapResponse(
        pull_request_id=pull_request.id,
        base_sha=diff.base_sha,
        head_sha=diff.head_sha,
        index_version=repository_map.index_version,
        source="git_diff+static_index+agent_evidence",
        nodes=nodes,
        edges=edges,
        truncated=truncated,
        message=(
            "Map is capped at 800 nodes; refine the view to inspect omitted impact nodes."
            if truncated
            else "Impact depth uses exact Head-side changed lines, parser ranges, confirmed static edges, and separately labelled Agent evidence."
        ),
    )


@router.get("/pull-requests/{pull_request_id}/graph", response_model=ReviewMapResponse)
def pull_request_graph(pull_request_id: str, session: SessionDependency) -> ReviewMapResponse:
    return _review_map(pull_request_id, session)


def _tour_category(path: str) -> tuple[int, str, str]:
    normalized = path.casefold()
    if any(part in normalized for part in ("route", "controller", "/api", "endpoint")):
        return 0, "API entry", "Review the externally reachable entry point and its request boundary."
    if any(part in normalized for part in ("schema", "types", "dto", "model")):
        return 1, "Parameters and data structures", "Review the changed data contract before its consumers."
    if any(part in normalized for part in ("database", "migration", "repository", "/db", ".sql")):
        return 3, "Data persistence", "Review persistence and migration effects after the calling logic."
    if any(part in normalized for part in ("test", "spec", "__tests__")):
        return 5, "Tests", "Review executable verification for the preceding production changes."
    if any(part in normalized for part in ("config", ".env", "toml", "yaml", "yml", "json")):
        return 6, "Configuration", "Review deployment and runtime configuration effects."
    return 2, "Core business logic", "Review the changed implementation and its static dependencies."


@router.get("/pull-requests/{pull_request_id}/tour", response_model=ChangeTourResponse)
def pull_request_tour(pull_request_id: str, session: SessionDependency) -> ChangeTourResponse:
    review = _review_map(pull_request_id, session)
    changed_paths = sorted(
        {
            node.path
            for node in review.nodes
            if node.path and node.kind == "file" and node.change_status is not None
        }
    )
    path_by_node = {node.id: node.path for node in review.nodes if node.path}
    dependencies: dict[str, set[str]] = {path: set() for path in changed_paths}
    relation_count: dict[str, int] = {path: 0 for path in changed_paths}
    for edge in review.edges:
        source_path = path_by_node.get(edge.source)
        target_path = path_by_node.get(edge.target)
        if (
            edge.confirmed
            and edge.kind in {"import", "call"}
            and source_path in dependencies
            and target_path in dependencies
            and source_path != target_path
        ):
            dependencies[source_path].add(target_path)
            relation_count[source_path] += 1
            relation_count[target_path] += 1

    remaining = set(changed_paths)
    ordered: list[str] = []
    while remaining:
        ready = [path for path in remaining if not (dependencies[path] & remaining)]
        if not ready:
            ready = list(remaining)
        ready.sort(key=lambda path: (_tour_category(path)[0], path))
        chosen = ready[0]
        ordered.append(chosen)
        remaining.remove(chosen)

    sequence_by_path = {path: index + 1 for index, path in enumerate(ordered)}
    steps = []
    for index, path in enumerate(ordered, start=1):
        path_nodes = [node for node in review.nodes if node.path == path]
        risks = [node.risk for node in path_nodes if node.risk]
        risk_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        risk = max(risks, key=lambda value: risk_order[value]) if risks else None
        prerequisites = sorted(
            (sequence_by_path[item] for item in dependencies[path] if sequence_by_path[item] < index),
            reverse=True,
        )
        _rank, title, purpose = _tour_category(path)
        has_relation = relation_count[path] > 0
        steps.append(
            {
                "sequence": index,
                "title": title,
                "files": [path],
                "symbols": sorted({node.symbol for node in path_nodes if node.symbol}),
                "purpose": purpose + " This classification is derived from the path and static index.",
                "prerequisite_step": prerequisites[0] if prerequisites else None,
                "risk": risk,
                "evidence_ids": sorted({item for node in path_nodes for item in node.evidence_ids}),
                "checkpoints": [
                    "Inspect the changed hunks in this file.",
                    "Confirm the indexed callers/importers shown in Review Map.",
                    "Validate any linked Finding against its cited Evidence.",
                ],
                "confidence": "high" if has_relation else "low",
            }
        )
    single_file = len(changed_paths) <= 1
    complete = single_file or all(relation_count[path] > 0 for path in changed_paths)
    if single_file:
        message = "Single changed indexed code file; no cross-file dependency order was inferred."
    elif complete:
        message = "Review order is grounded in confirmed static relationships."
    else:
        message = "Recommended order may be incomplete: one or more changed files have no confirmed static relationship."
    return ChangeTourResponse(
        pull_request_id=review.pull_request_id,
        head_sha=review.head_sha,
        source="git_diff+static_index+agent_evidence",
        complete=complete,
        message=message,
        steps=steps,
    )


@router.post("/pull-requests/{pull_request_id}/analyze", response_model=AnalyzeResponse)
async def analyze_pull_request(
    pull_request_id: str,
    request: Request,
    session: SessionDependency,
    force: bool = Query(default=False),
) -> AnalyzeResponse:
    pull_request = session.get(PullRequest, pull_request_id)
    if pull_request is None:
        raise StudioAPIError(404, "pull_request_not_found", "Pull Request was not found.")
    repository = _repository(session, pull_request.repository_id)
    if _settings_row(session).analysis_paused:
        raise StudioAPIError(
            409,
            "analysis_paused",
            "Analysis is paused in PR Inbox; resume analysis before starting a Run.",
        )
    if not pull_request.head_sha:
        raise StudioAPIError(409, "pull_request_head_missing", "Pull Request has no Head SHA.")
    if repository.current_commit_sha != pull_request.head_sha or not repository.current_index_version:
        raise StudioAPIError(
            409,
            "pull_request_index_mismatch",
            "Index the Pull Request Head SHA before starting analysis.",
        )
    try:
        model = configured_model(session)
    except ModelConfigurationError as exc:
        raise StudioAPIError(409, "model_not_configured", str(exc)) from exc
    try:
        result = enqueue_analysis_run(session, pull_request, repository, model, force=force)
    except ValueError as exc:
        raise StudioAPIError(409, "workflow_registry_disabled", str(exc)) from exc
    session.commit()
    session.refresh(result.run)
    if not result.reused:
        request.app.state.run_manager.start(result.run.id, model)
    return AnalyzeResponse(run=result.run, reused=result.reused)


@router.get("/runs", response_model=AgentRunListResponse)
def list_runs(
    session: SessionDependency,
    repository_id: str | None = None,
    pull_request_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AgentRunListResponse:
    filters = []
    if repository_id:
        filters.append(AgentRun.repository_id == repository_id)
    if pull_request_id:
        filters.append(AgentRun.pull_request_id == pull_request_id)
    if status:
        filters.append(AgentRun.status == status)
    total = int(session.scalar(select(func.count()).select_from(AgentRun).where(*filters)) or 0)
    rows = list(
        session.scalars(
            select(AgentRun).where(*filters).order_by(AgentRun.created_at.desc()).limit(limit).offset(offset)
        )
    )
    return AgentRunListResponse(items=rows, total=total, limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=AgentRunDetailResponse)
def get_run(run_id: str, session: SessionDependency) -> AgentRunDetailResponse:
    run = session.get(AgentRun, run_id)
    if run is None:
        raise StudioAPIError(404, "run_not_found", "Agent Run was not found.")
    steps = list(
        session.scalars(
            select(AgentStep).where(AgentStep.agent_run_id == run_id).order_by(AgentStep.sequence)
        )
    )
    step_ids = [step.id for step in steps]
    tool_calls = (
        list(
            session.scalars(
                select(ToolCallRecord)
                .where(ToolCallRecord.agent_step_id.in_(step_ids))
                .order_by(ToolCallRecord.id)
            )
        )
        if step_ids
        else []
    )
    return AgentRunDetailResponse(
        **AgentRunResponse.model_validate(run).model_dump(),
        steps=steps,
        tool_calls=tool_calls,
    )


@router.get("/runs/{run_id}/graph", response_model=AgentEvidenceGraphResponse)
def run_evidence_graph(run_id: str, session: SessionDependency) -> AgentEvidenceGraphResponse:
    run = session.get(AgentRun, run_id)
    if run is None:
        raise StudioAPIError(404, "run_not_found", "Agent Run was not found.")
    steps = list(
        session.scalars(
            select(AgentStep).where(AgentStep.agent_run_id == run_id).order_by(AgentStep.sequence)
        )
    )
    step_ids = [step.id for step in steps]
    tool_calls = (
        list(session.scalars(select(ToolCallRecord).where(ToolCallRecord.agent_step_id.in_(step_ids))))
        if step_ids
        else []
    )
    evidence = list(
        session.scalars(select(EvidenceRecord).where(EvidenceRecord.agent_run_id == run_id))
    )
    findings = list(session.scalars(select(Finding).where(Finding.agent_run_id == run_id)))
    nodes: list[dict[str, object]] = [
        {
            "id": f"task:{run.id}",
            "kind": "user_task",
            "label": "Pull Request review",
            "detail": f"run={run.id}",
            "status": run.status,
            "path": None,
            "line": None,
            "commit_sha": run.head_sha,
            "confidence": None,
        }
    ]
    edges: list[dict[str, object]] = []
    previous = f"task:{run.id}"
    for step in steps:
        node_id = f"step:{step.id}"
        nodes.append(
            {
                "id": node_id,
                "kind": "agent_step",
                "label": step.node,
                "detail": step.output_summary or step.error_message,
                "status": step.status,
                "path": None,
                "line": None,
                "commit_sha": run.head_sha,
                "confidence": None,
            }
        )
        edges.append(
            {
                "id": f"sequence:{previous}:{node_id}",
                "source": previous,
                "target": node_id,
                "kind": "workflow_sequence",
                "confirmed": True,
            }
        )
        previous = node_id
    for tool_call in tool_calls:
        node_id = f"tool:{tool_call.id}"
        nodes.append(
            {
                "id": node_id,
                "kind": "tool_call",
                "label": tool_call.tool_name,
                "detail": tool_call.output_summary,
                "status": tool_call.status,
                "path": None,
                "line": None,
                "commit_sha": run.head_sha,
                "confidence": None,
            }
        )
        edges.append(
            {
                "id": f"invoked:{tool_call.agent_step_id}:{tool_call.id}",
                "source": f"step:{tool_call.agent_step_id}",
                "target": node_id,
                "kind": "invoked",
                "confirmed": True,
            }
        )
    for record in evidence:
        node_id = f"evidence:{record.id}"
        line = record.payload_json.get("start_line")
        nodes.append(
            {
                "id": node_id,
                "kind": "evidence",
                "label": record.source_type,
                "detail": record.source_uri,
                "status": "persisted",
                "path": record.file_path,
                "line": line if isinstance(line, int) else None,
                "commit_sha": record.commit_sha,
                "confidence": None,
            }
        )
        edges.append(
            {
                "id": f"evidence-run:{record.id}",
                "source": f"task:{run.id}",
                "target": node_id,
                "kind": "persisted_for_run",
                "confirmed": True,
            }
        )
    evidence_ids = {record.id for record in evidence}
    for finding in findings:
        node_id = f"finding:{finding.id}"
        nodes.append(
            {
                "id": node_id,
                "kind": "finding",
                "label": finding.title,
                "detail": finding.message,
                "status": finding.verifier_status,
                "path": finding.file_path,
                "line": finding.line_start,
                "commit_sha": finding.commit_sha,
                "confidence": finding.confidence,
            }
        )
        linked = False
        for evidence_id in finding.evidence_ids_json:
            if evidence_id not in evidence_ids:
                continue
            linked = True
            edges.append(
                {
                    "id": f"supports:{evidence_id}:{finding.id}",
                    "source": f"evidence:{evidence_id}",
                    "target": node_id,
                    "kind": "supports",
                    "confirmed": finding.verifier_status == "verified",
                }
            )
        if not linked:
            edges.append(
                {
                    "id": f"finding-run:{finding.id}",
                    "source": f"task:{run.id}",
                    "target": node_id,
                    "kind": "persisted_for_run",
                    "confirmed": True,
                }
            )
    return AgentEvidenceGraphResponse(
        run_id=run.id,
        head_sha=run.head_sha,
        nodes=nodes,
        edges=edges,
        message="Edges represent persisted workflow sequence, tool ownership, run ownership, and cited Evidence only.",
    )


@router.post("/runs/{run_id}/cancel", response_model=AgentRunResponse)
def cancel_run(run_id: str, request: Request, session: SessionDependency) -> AgentRun:
    run = session.get(AgentRun, run_id)
    if run is None:
        raise StudioAPIError(404, "run_not_found", "Agent Run was not found.")
    if not request.app.state.run_manager.cancel(run_id):
        raise StudioAPIError(409, "run_not_cancellable", "Agent Run is already terminal.")
    session.expire(run)
    return run


@router.post("/runs/{run_id}/retry", response_model=AnalyzeResponse)
async def retry_run(run_id: str, request: Request, session: SessionDependency) -> AnalyzeResponse:
    previous = session.get(AgentRun, run_id)
    if previous is None or not previous.pull_request_id:
        raise StudioAPIError(404, "run_not_found", "Agent Run was not found.")
    return await analyze_pull_request(previous.pull_request_id, request, session, force=True)


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request, session: SessionDependency) -> StreamingResponse:
    if session.get(AgentRun, run_id) is None:
        raise StudioAPIError(404, "run_not_found", "Agent Run was not found.")
    session_factory = request.app.state.database.session_factory

    async def stream():  # type: ignore[no-untyped-def]
        last_sequence = 0
        while True:
            if await request.is_disconnected():
                return
            with session_factory() as event_session:
                steps = list(
                    event_session.scalars(
                        select(AgentStep)
                        .where(AgentStep.agent_run_id == run_id, AgentStep.sequence > last_sequence)
                        .order_by(AgentStep.sequence)
                    )
                )
                run = event_session.get(AgentRun, run_id)
                for step in steps:
                    last_sequence = step.sequence
                    payload = AgentStepResponse.model_validate(step).model_dump(mode="json")
                    yield f"event: step\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if run is None:
                    yield 'event: error\ndata: {"code":"run_not_found"}\n\n'
                    return
                if run.status in {"completed", "failed", "cancelled"}:
                    payload = AgentRunResponse.model_validate(run).model_dump(mode="json")
                    yield f"event: run\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    return
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/findings", response_model=list[FindingResponse])
def list_findings(
    session: SessionDependency,
    run_id: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Finding]:
    filters = []
    if run_id:
        filters.append(Finding.agent_run_id == run_id)
    if severity:
        filters.append(Finding.severity == severity)
    return list(session.scalars(select(Finding).where(*filters).order_by(Finding.created_at.desc()).limit(limit)))


@router.get("/evidence", response_model=list[EvidenceResponse])
def list_evidence(
    session: SessionDependency,
    run_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[EvidenceRecord]:
    statement = select(EvidenceRecord)
    if run_id:
        statement = statement.where(EvidenceRecord.agent_run_id == run_id)
    return list(session.scalars(statement.order_by(EvidenceRecord.created_at.desc()).limit(limit)))
