from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ComponentState = Literal["ready", "not_configured", "error", "unavailable"]
OnboardingStep = Literal[
    "welcome",
    "appearance",
    "github",
    "model",
    "repository",
    "background",
    "complete",
]


class ComponentStatus(BaseModel):
    state: ComponentState
    configured: bool
    message: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["tracegate-studio"] = "tracegate-studio"
    version: str
    api_version: Literal["v1"] = "v1"
    database: ComponentStatus


class SystemComponents(BaseModel):
    api: ComponentStatus
    database: ComponentStatus
    github: ComponentStatus
    model: ComponentStatus
    eval: ComponentStatus


class SystemStatusResponse(BaseModel):
    status: Literal["ready", "degraded", "error"]
    components: SystemComponents
    checked_at: datetime


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme: Literal["system", "light", "dark"]
    language: Literal["zh-CN", "en-US"]
    background_monitoring: bool
    launch_at_startup: bool
    model_provider: str | None
    model_base_url: str | None
    model_name: str | None
    updated_at: datetime


class SettingsUpdate(BaseModel):
    theme: Literal["system", "light", "dark"] | None = None
    language: Literal["zh-CN", "en-US"] | None = None
    background_monitoring: bool | None = None
    launch_at_startup: bool | None = None
    model_provider: str | None = Field(default=None, max_length=64)
    model_base_url: str | None = Field(default=None, max_length=2048)
    model_name: str | None = Field(default=None, max_length=255)

    @field_validator("model_provider", "model_name")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("model_base_url")
    @classmethod
    def validate_model_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().rstrip("/")
        if not normalized:
            return None
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("model_base_url must be an absolute HTTP(S) URL")
        return normalized

    @model_validator(mode="after")
    def require_update(self) -> "SettingsUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one settings field is required")
        for name in ("theme", "language", "background_monitoring", "launch_at_startup"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class OnboardingResponse(BaseModel):
    completed: bool
    current_step: OnboardingStep
    github: ComponentStatus
    model: ComponentStatus
    repository_added: bool
    background_monitoring: bool
    launch_at_startup: bool
    completed_at: datetime | None
    updated_at: datetime


class OnboardingUpdate(BaseModel):
    completed: bool | None = None
    current_step: OnboardingStep | None = None
    background_monitoring: bool | None = None
    launch_at_startup: bool | None = None

    @model_validator(mode="after")
    def require_update(self) -> "OnboardingUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one onboarding field is required")
        for name in (
            "completed",
            "current_step",
            "background_monitoring",
            "launch_at_startup",
        ):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


REPOSITORY_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class RepositoryCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=201)
    clone_url: str | None = Field(default=None, max_length=2048)
    local_path: str | None = Field(default=None, max_length=2048)
    default_branch: str | None = Field(default=None, max_length=255)
    monitoring_enabled: bool = False

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if not REPOSITORY_NAME_RE.fullmatch(normalized):
            raise ValueError("full_name must use the GitHub owner/name format")
        return normalized

    @field_validator("clone_url")
    @classmethod
    def validate_clone_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        parsed = urlsplit(normalized)
        if parsed.scheme != "https" or parsed.hostname != "github.com":
            raise ValueError("clone_url must be an HTTPS github.com URL")
        return normalized

    @field_validator("local_path", "default_branch")
    @classmethod
    def normalize_optional_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RepositoryUpdate(BaseModel):
    local_path: str | None = Field(default=None, max_length=2048)
    default_branch: str | None = Field(default=None, max_length=255)
    monitoring_enabled: bool | None = None

    @model_validator(mode="after")
    def require_update(self) -> "RepositoryUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one repository field is required")
        return self


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner: str
    name: str
    full_name: str
    clone_url: str | None
    local_path: str | None
    default_branch: str | None
    monitoring_enabled: bool
    connection_status: Literal["not_connected", "pending", "ready", "error"]
    last_error: str | None
    current_commit_sha: str | None
    current_index_version: str | None
    last_synced_at: datetime | None
    github_rate_remaining: int | None
    created_at: datetime
    updated_at: datetime


class RepositoryListResponse(BaseModel):
    items: list[RepositoryResponse]
    total: int
    limit: int
    offset: int


class RepositorySyncResponse(BaseModel):
    sync_id: str
    status: Literal["completed", "not_modified", "failed"]
    changed_pull_requests: int
    etag: str | None
    github_rate_remaining: int | None
    finished_at: datetime


class IndexVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    commit_sha: str
    status: str
    file_count: int
    symbol_count: int
    changed_count: int
    deleted_count: int
    duration_ms: int
    created_at: datetime


class GraphNodeResponse(BaseModel):
    id: str
    kind: str
    label: str
    path: str
    symbol: str | None
    language: str | None


class GraphEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    kind: str
    confirmed: bool


class RepositoryGraphResponse(BaseModel):
    repository_id: str
    commit_sha: str
    index_version: str
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    vector_search_enabled: Literal[False] = False
    vector_search_message: str = "Vector semantic retrieval is not enabled."


class PullRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    number: int
    title: str
    state: str
    url: str
    author: str | None
    base_sha: str | None
    head_sha: str | None
    draft: bool
    additions: int
    deletions: int
    changed_files: int
    analysis_status: str
    updated_at_github: datetime | None
    created_at: datetime
    updated_at: datetime


class PullRequestListResponse(BaseModel):
    items: list[PullRequestResponse]
    total: int
    limit: int
    offset: int


class ChangedFileResponse(BaseModel):
    path: str
    status: str


class PullRequestDiffResponse(BaseModel):
    pull_request_id: str
    base_sha: str
    head_sha: str
    changed_files: list[ChangedFileResponse]
    selected_path: str | None
    original: str | None
    modified: str | None
    unified_diff: str


class RetrievalHitResponse(BaseModel):
    kind: str
    path: str
    score: float
    source: str
    snippet: str
    symbol: str | None
    line: int | None


class RetrievalResponse(BaseModel):
    repository_id: str
    index_version: str
    commit_sha: str
    query: str
    hits: list[RetrievalHitResponse]
    vector_search_enabled: bool
    vector_search_message: str


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    pull_request_id: str | None
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    current_node: str | None
    head_sha: str | None
    prompt_version: str | None
    index_version: str | None
    workflow_version: str | None
    model_profile: str | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    retry_count: int
    cancellation_requested: bool
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentRunListResponse(BaseModel):
    items: list[AgentRunResponse]
    total: int
    limit: int
    offset: int


class AnalyzeResponse(BaseModel):
    run: AgentRunResponse
    reused: bool


class AgentStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_run_id: str
    sequence: int
    node: str
    status: str
    input_summary: str | None
    output_summary: str | None
    error_code: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None


class ToolCallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_step_id: str
    tool_name: str
    permission: str
    arguments_summary: str
    output_summary: str | None
    status: str
    duration_ms: int | None
    error_code: str | None


class AgentRunDetailResponse(AgentRunResponse):
    steps: list[AgentStepResponse]
    tool_calls: list[ToolCallResponse]


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_run_id: str
    severity: str
    confidence: float
    category: str
    title: str
    message: str
    file_path: str | None
    line_start: int | None
    line_end: int | None
    commit_sha: str | None
    symbol: str | None
    evidence_ids_json: list[str]
    suggested_action: str | None
    verifier_status: str
    model_profile: str | None
    created_at: datetime


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_run_id: str
    source_type: str
    source_uri: str
    file_path: str | None
    commit_sha: str | None
    content_hash: str
    payload_json: dict[str, object]
    created_at: datetime


class EvaluationArtifactResponse(BaseModel):
    path: str
    sha256: str


class EvaluationCaseResponse(BaseModel):
    model: str
    task_id: str
    evidence_status: str
    expected_decision: str
    decision: str
    context_group: str
    claimbench_status: str
    safe_success: bool
    evidence_aware_decision: bool
    context_tokens: int
    run_dir: str


class EvaluationSummaryResponse(BaseModel):
    benchmark_name: str
    benchmark_note: str
    dataset_sha256: str
    is_real_dataset: Literal[True]
    case_count: int
    claimbench_run_count: int
    status_distribution: dict[str, int]
    risk_distribution: dict[str, int]
    decision_distribution: dict[str, int]
    metrics: dict[str, float]
    models: dict[str, int]
    context_groups: dict[str, int]
    claimbench_status_distribution: dict[str, int]
    claimbench_decision_distribution: dict[str, int]
    limitations: list[str]
    artifacts: list[EvaluationArtifactResponse]
    cases: list[EvaluationCaseResponse]


class AgentDescriptorResponse(BaseModel):
    name: str
    version: str
    responsibility: str
    status: Literal["enabled"]
    capabilities: list[str]
    allowed_tools: list[str]


class ToolDescriptorResponse(BaseModel):
    name: str
    description: str
    permission: Literal[
        "SAFE_READ",
        "REPOSITORY_READ",
        "COMMAND_RESTRICTED",
        "WRITE_CONFIRMATION",
        "NETWORK",
        "DESTRUCTIVE_FORBIDDEN",
    ]
    timeout_seconds: float
    max_output_bytes: int
    input_schema: dict[str, object]
    enabled: bool
    recent_call_count: int
    recent_error_count: int
    most_recent_error: str | None


class ReviewMapNodeResponse(BaseModel):
    id: str
    kind: str
    label: str
    path: str | None
    symbol: str | None
    language: str | None
    impact_depth: int
    change_status: Literal["added", "modified", "deleted", "renamed"] | None
    risk: Literal["info", "low", "medium", "high", "critical"] | None
    finding_ids: list[str]
    evidence_ids: list[str]


class ReviewMapEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    kind: str
    confirmed: bool


class ReviewMapResponse(BaseModel):
    pull_request_id: str
    base_sha: str
    head_sha: str
    index_version: str
    source: Literal["git_diff+static_index+agent_evidence"]
    nodes: list[ReviewMapNodeResponse]
    edges: list[ReviewMapEdgeResponse]
    truncated: bool
    message: str


class ChangeTourStepResponse(BaseModel):
    sequence: int
    title: str
    files: list[str]
    symbols: list[str]
    purpose: str
    prerequisite_step: int | None
    risk: str | None
    evidence_ids: list[str]
    checkpoints: list[str]
    confidence: Literal["high", "medium", "low"]


class ChangeTourResponse(BaseModel):
    pull_request_id: str
    head_sha: str
    source: Literal["git_diff+static_index+agent_evidence"]
    complete: bool
    message: str
    steps: list[ChangeTourStepResponse]


class MonitorDiagnosticResponse(BaseModel):
    running: bool
    polling: bool
    queued_repositories: int
    last_started_at: datetime | None
    last_finished_at: datetime | None
    last_error: str | None


class DiagnosticsResponse(BaseModel):
    software_version: str
    git_commit: str | None
    operating_system: str
    architecture: str
    python_version: str
    frontend_version: str | None
    desktop_version: str | None
    database_type: str
    database_path: str | None
    log_path: str
    workspace_paths: list[str]
    sidecar_pid: int
    api_port: int
    github: ComponentStatus
    model: ComponentStatus
    monitor: MonitorDiagnosticResponse
    agent_queue: int
    index_queue: int
    telemetry_enabled: Literal[False]


class AgentEvidenceGraphNodeResponse(BaseModel):
    id: str
    kind: str
    label: str
    detail: str | None
    status: str | None
    path: str | None
    line: int | None
    commit_sha: str | None
    confidence: float | None


class AgentEvidenceGraphEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    kind: str
    confirmed: bool


class AgentEvidenceGraphResponse(BaseModel):
    run_id: str
    head_sha: str | None
    nodes: list[AgentEvidenceGraphNodeResponse]
    edges: list[AgentEvidenceGraphEdgeResponse]
    message: str


class UpdateStatusResponse(BaseModel):
    current_version: str
    channel: Literal["stable"]
    configured: bool
    update_available: bool
    latest_version: str | None
    manifest_url: str | None
    signature_verification: bool
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
