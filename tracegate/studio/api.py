from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import StudioSettings
from .errors import StudioAPIError
from .eval_bridge import eval_component_status
from .github_sync import sync_repository_pull_requests
from .index_store import RepositoryIndexError, load_repository_map, persist_repository_index
from .models import AgentRun, AgentStep, AppSettings, EvidenceRecord, Finding, OnboardingState, PullRequest, Repository
from .run_manager import configured_model
from .schemas import (
    ComponentStatus,
    AgentRunListResponse,
    AgentRunResponse,
    AgentStepResponse,
    AnalyzeResponse,
    EvidenceResponse,
    FindingResponse,
    HealthResponse,
    OnboardingResponse,
    OnboardingUpdate,
    IndexVersionResponse,
    PullRequestListResponse,
    PullRequestResponse,
    RepositoryCreate,
    RepositoryGraphResponse,
    RepositoryListResponse,
    RepositoryResponse,
    RepositorySyncResponse,
    RetrievalResponse,
    RepositoryUpdate,
    SettingsResponse,
    SettingsUpdate,
    SystemComponents,
    SystemStatusResponse,
)
from .security import require_local_token
from tracegate.github import GitHubAPIError
from tracegate.repository import RepositoryBoundary, RepositoryPathError
from tracegate.retrieval import hybrid_retrieve
from tracegate.models import ModelConfigurationError
from tracegate.agent.workflow import PROMPT_VERSION, WORKFLOW_VERSION


router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_local_token)])


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
            message="GitHub is not connected.",
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
            message="Model is not configured.",
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
        eval=eval_status,
    )
    states = [component.state for component in components.__dict__.values()]
    status = "error" if "error" in states else "degraded" if any(
        state in {"not_configured", "unavailable"} for state in states
    ) else "ready"
    return SystemStatusResponse(status=status, components=components, checked_at=utcnow())


@router.get("/settings", response_model=SettingsResponse)
def get_settings(session: SessionDependency) -> AppSettings:
    return _settings_row(session)


@router.put("/settings", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate, session: SessionDependency) -> AppSettings:
    row = _settings_row(session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.updated_at = utcnow()
    session.commit()
    session.refresh(row)
    return row


def _onboarding_response(
    settings: StudioSettings,
    app_settings: AppSettings,
    onboarding: OnboardingState,
    repository_added: bool,
) -> OnboardingResponse:
    return OnboardingResponse(
        completed=onboarding.completed,
        current_step=onboarding.current_step,
        github=_github_status(settings),
        model=_model_status(settings, app_settings),
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
    repository_added = bool(session.scalar(select(func.count()).select_from(Repository)))
    return _onboarding_response(
        request.app.state.settings,
        app_settings,
        onboarding,
        repository_added,
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


@router.put("/repositories/{repository_id}", response_model=RepositoryResponse)
def update_repository(
    repository_id: str,
    payload: RepositoryUpdate,
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
        edges=[edge.__dict__ for edge in repository_map.edges],
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
    if not force:
        existing = session.scalar(
            select(AgentRun)
            .where(
                AgentRun.pull_request_id == pull_request.id,
                AgentRun.head_sha == pull_request.head_sha,
                AgentRun.index_version == repository.current_index_version,
                AgentRun.prompt_version == PROMPT_VERSION,
                AgentRun.model_profile == model.profile,
                AgentRun.status.in_(["queued", "running", "completed"]),
            )
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        if existing is not None:
            return AnalyzeResponse(run=existing, reused=True)
    run = AgentRun(
        repository_id=repository.id,
        pull_request_id=pull_request.id,
        status="queued",
        head_sha=pull_request.head_sha,
        index_version=repository.current_index_version,
        prompt_version=PROMPT_VERSION,
        workflow_version=WORKFLOW_VERSION,
        model_profile=model.profile,
    )
    pull_request.analysis_status = "queued"
    session.add(run)
    session.commit()
    session.refresh(run)
    request.app.state.run_manager.start(run.id, model)
    return AnalyzeResponse(run=run, reused=False)


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


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
def get_run(run_id: str, session: SessionDependency) -> AgentRun:
    run = session.get(AgentRun, run_id)
    if run is None:
        raise StudioAPIError(404, "run_not_found", "Agent Run was not found.")
    return run


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
