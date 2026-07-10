from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import StudioSettings
from .errors import StudioAPIError
from .eval_bridge import eval_component_status
from .models import AppSettings, OnboardingState, Repository
from .schemas import (
    ComponentStatus,
    HealthResponse,
    OnboardingResponse,
    OnboardingUpdate,
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryResponse,
    RepositoryUpdate,
    SettingsResponse,
    SettingsUpdate,
    SystemComponents,
    SystemStatusResponse,
)
from .security import require_local_token


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
    repository = Repository(
        owner=owner,
        name=name,
        full_name=payload.full_name,
        clone_url=payload.clone_url or f"https://github.com/{payload.full_name}.git",
        local_path=payload.local_path,
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
    for field, value in payload.model_dump(exclude_unset=True).items():
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
