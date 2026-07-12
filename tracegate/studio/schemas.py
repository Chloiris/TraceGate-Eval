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
    webhook_relay: ComponentStatus
    eval: ComponentStatus


class SystemStatusResponse(BaseModel):
    status: Literal["ready", "degraded", "error"]
    components: SystemComponents
    checked_at: datetime


class ConnectionTestRequest(BaseModel):
    component: Literal["backend", "github", "model"]


class ConnectionTestResponse(BaseModel):
    component: Literal["backend", "github", "model"]
    status: Literal["ready"] = "ready"
    message: str
    detail: str | None = None
    latency_ms: int = Field(ge=0)


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme: Literal["system", "light", "dark"]
    language: Literal["zh-CN", "en-US"]
    background_monitoring: bool
    launch_at_startup: bool
    close_notice_dismissed: bool
    notifications_enabled: bool
    model_provider: str | None
    model_base_url: str | None
    model_name: str | None
    model_temperature: float
    model_max_output_tokens: int
    model_timeout_seconds: int
    model_max_retries: int
    model_native_structured_output: bool
    model_streaming_enabled: bool
    model_native_tool_calling: bool
    model_context_scope: Literal["changed_files", "retrieved_context"]
    model_input_cost_per_million: float
    model_output_cost_per_million: float
    github_poll_interval_seconds: int
    automatic_analysis_enabled: bool
    automatic_analysis_include_drafts: bool
    automatic_analysis_require_checks_success: bool
    analysis_paused: bool
    webhook_relay_url: str | None
    webhook_relay_device_id: str | None
    autofix_max_files: int
    autofix_max_changed_lines: int
    autofix_confirmation_ttl_seconds: int
    autofix_workspace_retention_hours: int
    updated_at: datetime


class SettingsUpdate(BaseModel):
    theme: Literal["system", "light", "dark"] | None = None
    language: Literal["zh-CN", "en-US"] | None = None
    background_monitoring: bool | None = None
    launch_at_startup: bool | None = None
    close_notice_dismissed: bool | None = None
    notifications_enabled: bool | None = None
    model_provider: str | None = Field(default=None, max_length=64)
    model_base_url: str | None = Field(default=None, max_length=2048)
    model_name: str | None = Field(default=None, max_length=255)
    model_temperature: float | None = Field(default=None, ge=0, le=2)
    model_max_output_tokens: int | None = Field(default=None, ge=256, le=32768)
    model_timeout_seconds: int | None = Field(default=None, ge=5, le=300)
    model_max_retries: int | None = Field(default=None, ge=0, le=3)
    model_native_structured_output: bool | None = None
    model_streaming_enabled: bool | None = None
    model_native_tool_calling: bool | None = None
    model_context_scope: Literal["changed_files", "retrieved_context"] | None = None
    model_input_cost_per_million: float | None = Field(default=None, ge=0, le=10000)
    model_output_cost_per_million: float | None = Field(default=None, ge=0, le=10000)
    github_poll_interval_seconds: int | None = Field(default=None, ge=30, le=3600)
    automatic_analysis_enabled: bool | None = None
    automatic_analysis_include_drafts: bool | None = None
    automatic_analysis_require_checks_success: bool | None = None
    analysis_paused: bool | None = None
    webhook_relay_url: str | None = Field(default=None, max_length=2048)
    webhook_relay_device_id: str | None = Field(default=None, max_length=128)
    autofix_max_files: int | None = Field(default=None, ge=1, le=32)
    autofix_max_changed_lines: int | None = Field(default=None, ge=50, le=5000)
    autofix_confirmation_ttl_seconds: int | None = Field(default=None, ge=60, le=3600)
    autofix_workspace_retention_hours: int | None = Field(default=None, ge=1, le=168)

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
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "model_base_url must not contain credentials, query, or fragment"
            )
        return normalized

    @field_validator("webhook_relay_url")
    @classmethod
    def validate_webhook_relay_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().rstrip("/")
        if not normalized:
            return None
        parsed = urlsplit(normalized)
        loopback_http = parsed.scheme == "http" and parsed.hostname in {
            "127.0.0.1",
            "localhost",
            "::1",
        }
        if (parsed.scheme != "https" and not loopback_http) or not parsed.netloc:
            raise ValueError("webhook_relay_url must use HTTPS or loopback HTTP")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "webhook_relay_url must not contain credentials, query, or fragment"
            )
        return normalized

    @field_validator("webhook_relay_device_id")
    @classmethod
    def validate_webhook_relay_device_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", normalized):
            raise ValueError("webhook_relay_device_id is invalid")
        return normalized

    @model_validator(mode="after")
    def require_update(self) -> "SettingsUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one settings field is required")
        for name in (
            "theme",
            "language",
            "background_monitoring",
            "launch_at_startup",
            "close_notice_dismissed",
            "notifications_enabled",
            "model_temperature",
            "model_max_output_tokens",
            "model_timeout_seconds",
            "model_max_retries",
            "model_native_structured_output",
            "model_streaming_enabled",
            "model_native_tool_calling",
            "model_context_scope",
            "model_input_cost_per_million",
            "model_output_cost_per_million",
            "github_poll_interval_seconds",
            "automatic_analysis_enabled",
            "automatic_analysis_include_drafts",
            "automatic_analysis_require_checks_success",
            "analysis_paused",
            "autofix_max_files",
            "autofix_max_changed_lines",
            "autofix_confirmation_ttl_seconds",
            "autofix_workspace_retention_hours",
        ):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class OnboardingResponse(BaseModel):
    completed: bool
    current_step: OnboardingStep
    github: ComponentStatus
    model: ComponentStatus
    webhook_relay: ComponentStatus
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


class RepositorySummaryResponse(BaseModel):
    repository_id: str
    commit_sha: str | None
    index_version: str | None
    file_count: int = Field(ge=0)
    directory_count: int = Field(ge=0)
    symbol_count: int = Field(ge=0)
    dependency_edge_count: int = Field(ge=0)
    language_counts: dict[str, int]
    active_pull_requests: int = Field(ge=0)


class RepositorySyncResponse(BaseModel):
    sync_id: str
    status: Literal["completed", "not_modified", "failed"]
    changed_pull_requests: int
    changed_check_runs: int
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
    index_duration_ms: int
    graph_duration_ms: int
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
    base_ref: str | None
    head_ref: str | None
    base_sha: str | None
    head_sha: str | None
    draft: bool
    additions: int
    deletions: int
    changed_files: int
    analysis_status: str
    checks_status: Literal["not_available", "pending", "success", "failure", "neutral"]
    last_checks_synced_at: datetime | None
    risk_level: Literal["info", "low", "medium", "high", "critical"] | None
    risk_score: float | None
    conclusion_summary: str | None
    impact_paths_json: list[str]
    recommended_review_order_json: list[str]
    latest_model_profile: str | None
    updated_at_github: datetime | None
    created_at: datetime
    updated_at: datetime


class PullRequestListResponse(BaseModel):
    items: list[PullRequestResponse]
    total: int
    limit: int
    offset: int


class CheckRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    github_id: int
    pull_request_id: str
    head_sha: str
    name: str
    status: str
    conclusion: str | None
    details_url: str | None
    app_name: str | None
    started_at: datetime | None
    completed_at: datetime | None
    synced_at: datetime


class CheckRunListResponse(BaseModel):
    items: list[CheckRunResponse]
    aggregate_status: Literal[
        "not_available", "pending", "success", "failure", "neutral"
    ]
    synced_at: datetime | None


class CommitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pull_request_id: str
    sha: str
    message: str
    author_name: str | None
    author_email: str | None
    author_login: str | None
    authored_at: datetime | None
    html_url: str | None
    position: int
    synced_at: datetime


class ChangedHunkDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence: int
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    patch: str
    patch_hash: str


class ChangedFileDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pull_request_id: str
    head_sha: str
    blob_sha: str
    path: str
    previous_path: str | None
    status: str
    additions: int
    deletions: int
    changes: int
    blob_url: str | None
    raw_url: str | None
    contents_url: str | None
    patch_hash: str | None
    synced_at: datetime
    hunks: list[ChangedHunkDetailResponse]


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
    model_profile_id: str | None = None
    context_scope: Literal["changed_files", "retrieved_context"]
    input_tokens: int
    output_tokens: int
    latency_ms: int
    retry_count: int
    retrieval_hit_count: int
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


NotificationKind = Literal[
    "new_pull_request",
    "new_pull_request_commit",
    "analysis_started",
    "high_risk_finding",
    "analysis_completed",
    "analysis_failed",
    "github_authentication_failed",
    "sidecar_restart_failed",
    "test",
]


class NotificationCreate(BaseModel):
    kind: NotificationKind
    status: Literal["delivered", "failed"]
    title: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=4000)
    deep_link: str | None = Field(default=None, max_length=2048)
    repository_id: str | None = None
    pull_request_id: str | None = None
    agent_run_id: str | None = None
    error_message: str | None = Field(default=None, max_length=4000)

    @field_validator("deep_link")
    @classmethod
    def validate_deep_link(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("tracegate://"):
            raise ValueError("deep_link must use the tracegate scheme")
        return value

    @model_validator(mode="after")
    def validate_status_error(self) -> "NotificationCreate":
        if self.status == "failed" and not self.error_message:
            raise ValueError("failed notifications require error_message")
        if self.status == "delivered" and self.error_message is not None:
            raise ValueError("delivered notifications cannot include error_message")
        return self


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: NotificationKind
    status: Literal["delivered", "failed"]
    title: str
    body: str
    deep_link: str | None
    repository_id: str | None
    pull_request_id: str | None
    agent_run_id: str | None
    error_message: str | None
    attempted_at: datetime


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
    status: Literal["enabled", "disabled"]
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


class RegistryToggleRequest(BaseModel):
    enabled: bool


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
    rate_limited_until: datetime | None


class RelayMonitorDiagnosticResponse(BaseModel):
    running: bool
    connected: bool
    reconnect_count: int
    last_connected_at: datetime | None
    last_event_at: datetime | None
    last_repository: str | None
    last_error: str | None


class DiagnosticsResponse(BaseModel):
    software_version: str
    git_commit: str | None
    operating_system: str
    architecture: str
    python_version: str
    frontend_version: str | None
    desktop_version: str | None
    rust_version_info: str | None
    log_level: str
    database_type: str
    database_path: str | None
    log_path: str
    workspace_paths: list[str]
    sidecar_pid: int
    api_port: int
    github: ComponentStatus
    model: ComponentStatus
    webhook_relay: ComponentStatus
    monitor: MonitorDiagnosticResponse
    relay_monitor: RelayMonitorDiagnosticResponse
    agent_queue: int
    index_queue: int
    last_github_api_request_count: int | None
    last_github_api_duration_ms: int | None
    last_index_duration_ms: int | None
    last_graph_duration_ms: int | None
    last_retrieval_result_count: int | None
    last_model_latency_ms: int | None
    last_model_input_tokens: int | None
    last_model_output_tokens: int | None
    last_model_retry_count: int | None
    delivered_notification_count: int
    failed_notification_count: int
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
