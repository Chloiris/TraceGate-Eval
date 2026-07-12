from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from tracegate.autofix.schemas import (
    FixEligibilityStatus,
    FixPermissionMode,
    FixResolution,
    FixSessionStatus,
    ValidationStatus,
)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Declarative base for the isolated Studio persistence schema."""


def _enum_sql(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{item.value}'" for item in enum_type)


FIX_WORKSPACE_CLEANUP_STATUSES = (
    "NOT_CREATED",
    "ACTIVE",
    "CLEANUP_PENDING",
    "DELETED",
    "CLEANUP_FAILED",
    "RETAINED",
)


class AppSettings(Base):
    __tablename__ = "app_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_app_settings_singleton"),
        CheckConstraint(
            "theme IN ('system', 'light', 'dark')", name="ck_app_settings_theme"
        ),
        CheckConstraint(
            "language IN ('zh-CN', 'en-US')", name="ck_app_settings_language"
        ),
        CheckConstraint(
            "model_temperature >= 0 AND model_temperature <= 2",
            name="ck_app_settings_model_temperature",
        ),
        CheckConstraint(
            "model_max_output_tokens >= 256 AND model_max_output_tokens <= 32768",
            name="ck_app_settings_model_max_output_tokens",
        ),
        CheckConstraint(
            "model_timeout_seconds >= 5 AND model_timeout_seconds <= 300",
            name="ck_app_settings_model_timeout_seconds",
        ),
        CheckConstraint(
            "model_max_retries >= 0 AND model_max_retries <= 3",
            name="ck_app_settings_model_max_retries",
        ),
        CheckConstraint(
            "model_context_scope IN ('changed_files', 'retrieved_context')",
            name="ck_app_settings_model_context_scope",
        ),
        CheckConstraint(
            "model_input_cost_per_million >= 0 AND model_output_cost_per_million >= 0",
            name="ck_app_settings_model_costs",
        ),
        CheckConstraint(
            "github_poll_interval_seconds >= 30 AND github_poll_interval_seconds <= 3600",
            name="ck_app_settings_github_poll_interval_seconds",
        ),
        CheckConstraint(
            "autofix_max_files >= 1 AND autofix_max_files <= 32",
            name="ck_app_settings_autofix_max_files",
        ),
        CheckConstraint(
            "autofix_max_changed_lines >= 50 AND autofix_max_changed_lines <= 5000",
            name="ck_app_settings_autofix_max_changed_lines",
        ),
        CheckConstraint(
            "autofix_confirmation_ttl_seconds >= 60 AND autofix_confirmation_ttl_seconds <= 3600",
            name="ck_app_settings_autofix_confirmation_ttl_seconds",
        ),
        CheckConstraint(
            "autofix_workspace_retention_hours >= 1 AND autofix_workspace_retention_hours <= 168",
            name="ck_app_settings_autofix_workspace_retention_hours",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False, default=1
    )
    theme: Mapped[str] = mapped_column(String(16), nullable=False, default="system")
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="zh-CN")
    background_monitoring: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    launch_at_startup: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    close_notice_dismissed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    model_provider: Mapped[str | None] = mapped_column(String(64))
    model_base_url: Mapped[str | None] = mapped_column(String(2048))
    model_name: Mapped[str | None] = mapped_column(String(255))
    model_temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_max_output_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=4096
    )
    model_timeout_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    model_max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    model_native_structured_output: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    model_streaming_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    model_native_tool_calling: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    model_context_scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="changed_files"
    )
    model_input_cost_per_million: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    model_output_cost_per_million: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    github_poll_interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    automatic_analysis_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    automatic_analysis_include_drafts: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    automatic_analysis_require_checks_success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    analysis_paused: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    webhook_relay_url: Mapped[str | None] = mapped_column(String(2048))
    webhook_relay_device_id: Mapped[str | None] = mapped_column(String(128))
    disabled_agents_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    disabled_tools_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    autofix_max_files: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    autofix_max_changed_lines: Mapped[int] = mapped_column(
        Integer, nullable=False, default=800
    )
    autofix_confirmation_ttl_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=900
    )
    autofix_workspace_retention_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=24
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class OnboardingState(Base):
    __tablename__ = "onboarding_state"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_onboarding_state_singleton"),
        CheckConstraint(
            "current_step IN ('welcome', 'appearance', 'github', 'model', 'repository', 'background', 'complete')",
            name="ck_onboarding_state_step",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False, default=1
    )
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_step: Mapped[str] = mapped_column(
        String(32), nullable=False, default="welcome"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("full_name", name="uq_repositories_full_name"),
        CheckConstraint(
            "connection_status IN ('not_connected', 'pending', 'ready', 'error')",
            name="ck_repositories_connection_status",
        ),
        Index("ix_repositories_monitoring_enabled", "monitoring_enabled"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(201), nullable=False)
    clone_url: Mapped[str | None] = mapped_column(String(2048))
    local_path: Mapped[str | None] = mapped_column(String(2048))
    default_branch: Mapped[str | None] = mapped_column(String(255))
    monitoring_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    connection_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_connected"
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    current_commit_sha: Mapped[str | None] = mapped_column(String(64))
    current_index_version: Mapped[str | None] = mapped_column(String(36))
    sync_etag: Mapped[str | None] = mapped_column(String(512))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    github_rate_remaining: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "number", name="uq_pull_requests_repository_number"
        ),
        Index("ix_pull_requests_repository_state", "repository_id", "state"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255))
    base_ref: Mapped[str | None] = mapped_column(String(255))
    head_ref: Mapped[str | None] = mapped_column(String(255))
    base_sha: Mapped[str | None] = mapped_column(String(64))
    head_sha: Mapped[str | None] = mapped_column(String(64))
    updated_at_github: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    additions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deletions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_analyzed"
    )
    checks_etag: Mapped[str | None] = mapped_column(String(512))
    checks_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_available"
    )
    last_checks_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    risk_level: Mapped[str | None] = mapped_column(String(16))
    risk_score: Mapped[float | None] = mapped_column(Float)
    conclusion_summary: Mapped[str | None] = mapped_column(Text)
    impact_paths_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    recommended_review_order_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    latest_model_profile: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class CommitRecord(Base):
    __tablename__ = "commits"
    __table_args__ = (
        UniqueConstraint("pull_request_id", "sha", name="uq_commits_pr_sha"),
        Index("ix_commits_pr_position", "pull_request_id", "position"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pull_request_id: Mapped[str] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False
    )
    sha: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(255))
    author_email: Mapped[str | None] = mapped_column(String(320))
    author_login: Mapped[str | None] = mapped_column(String(255))
    authored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    html_url: Mapped[str | None] = mapped_column(String(2048))
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class ChangedFileRecord(Base):
    __tablename__ = "changed_files"
    __table_args__ = (
        UniqueConstraint(
            "pull_request_id", "head_sha", "path", name="uq_changed_files_pr_head_path"
        ),
        Index("ix_changed_files_pr_head", "pull_request_id", "head_sha"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pull_request_id: Mapped[str] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False
    )
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    blob_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    previous_path: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    additions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deletions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blob_url: Mapped[str | None] = mapped_column(String(2048))
    raw_url: Mapped[str | None] = mapped_column(String(2048))
    contents_url: Mapped[str | None] = mapped_column(String(2048))
    patch: Mapped[str | None] = mapped_column(Text)
    patch_hash: Mapped[str | None] = mapped_column(String(64))
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class ChangedHunkRecord(Base):
    __tablename__ = "changed_hunks"
    __table_args__ = (
        UniqueConstraint(
            "changed_file_id", "sequence", name="uq_changed_hunks_file_sequence"
        ),
        Index("ix_changed_hunks_file_new_start", "changed_file_id", "new_start"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    changed_file_id: Mapped[str] = mapped_column(
        ForeignKey("changed_files.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    header: Mapped[str] = mapped_column(String(1024), nullable=False)
    old_start: Mapped[int] = mapped_column(Integer, nullable=False)
    old_count: Mapped[int] = mapped_column(Integer, nullable=False)
    new_start: Mapped[int] = mapped_column(Integer, nullable=False)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False)
    patch: Mapped[str] = mapped_column(Text, nullable=False)
    patch_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class RepositorySync(Base):
    __tablename__ = "repository_syncs"
    __table_args__ = (
        Index("ix_repository_syncs_repository_started", "repository_id", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    etag: Mapped[str | None] = mapped_column(String(512))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    changed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checks_changed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    github_api_request_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    github_api_duration_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PullRequestSnapshot(Base):
    __tablename__ = "pull_request_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "pull_request_id",
            "head_sha",
            "payload_hash",
            name="uq_pr_snapshot_head_payload",
        ),
        Index("ix_pr_snapshots_pr_captured", "pull_request_id", "captured_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pull_request_id: Mapped[str] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False
    )
    base_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class CheckRunRecord(Base):
    __tablename__ = "check_runs"
    __table_args__ = (
        UniqueConstraint(
            "pull_request_id", "github_id", name="uq_check_runs_pr_github_id"
        ),
        Index("ix_check_runs_pr_status", "pull_request_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pull_request_id: Mapped[str] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False
    )
    github_id: Mapped[int] = mapped_column(Integer, nullable=False)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    conclusion: Mapped[str | None] = mapped_column(String(64))
    details_url: Mapped[str | None] = mapped_column(String(2048))
    app_name: Mapped[str | None] = mapped_column(String(255))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class IndexVersion(Base):
    __tablename__ = "index_versions"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "commit_sha", name="uq_index_repository_commit"
        ),
        Index("ix_index_versions_repository_created", "repository_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol_count: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    deleted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    index_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    graph_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class IndexedFile(Base):
    __tablename__ = "indexed_files"
    __table_args__ = (
        UniqueConstraint(
            "index_version_id", "path", name="uq_indexed_file_version_path"
        ),
        Index("ix_indexed_files_version_language", "index_version_id", "language"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    index_version_id: Mapped[str] = mapped_column(
        ForeignKey("index_versions.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    capabilities_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    imports_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    exports_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    references_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    relationships_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)


class IndexedSymbol(Base):
    __tablename__ = "indexed_symbols"
    __table_args__ = (Index("ix_indexed_symbols_file_name", "indexed_file_id", "name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    indexed_file_id: Mapped[str] = mapped_column(
        ForeignKey("indexed_files.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    qualified_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)


class GraphNodeRecord(Base):
    __tablename__ = "graph_nodes"
    __table_args__ = (Index("ix_graph_nodes_version_kind", "index_version_id", "kind"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    index_version_id: Mapped[str] = mapped_column(
        ForeignKey("index_versions.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(1024), nullable=False)
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(1024))
    language: Mapped[str | None] = mapped_column(String(32))


class GraphEdgeRecord(Base):
    __tablename__ = "graph_edges"
    __table_args__ = (Index("ix_graph_edges_version_kind", "index_version_id", "kind"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    index_version_id: Mapped[str] = mapped_column(
        ForeignKey("index_versions.id", ondelete="CASCADE"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ModelProfile(Base):
    __tablename__ = "model_profiles"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_model_profiles_fingerprint"),
        Index("ix_model_profiles_provider_model", "provider", "model_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_label: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False)
    native_structured_output: Mapped[bool] = mapped_column(Boolean, nullable=False)
    streaming_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    native_tool_calling: Mapped[bool] = mapped_column(Boolean, nullable=False)
    context_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    input_cost_per_million: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    output_cost_per_million: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_agent_runs_status",
        ),
        Index("ix_agent_runs_repository_status", "repository_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    pull_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    current_node: Mapped[str | None] = mapped_column(String(128))
    head_sha: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    index_version: Mapped[str | None] = mapped_column(String(64))
    workflow_version: Mapped[str | None] = mapped_column(String(64))
    model_profile: Mapped[str | None] = mapped_column(String(255))
    model_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("model_profiles.id", ondelete="SET NULL")
    )
    context_scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="changed_files"
    )
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retrieval_hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancellation_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class AgentStep(Base):
    __tablename__ = "agent_steps"
    __table_args__ = (
        UniqueConstraint("agent_run_id", "sequence", name="uq_agent_step_run_sequence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    node: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_summary: Mapped[str | None] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class ToolCallRecord(Base):
    __tablename__ = "tool_calls"
    __table_args__ = (Index("ix_tool_calls_step_tool", "agent_step_id", "tool_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_step_id: Mapped[str] = mapped_column(
        ForeignKey("agent_steps.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    permission: Mapped[str] = mapped_column(String(64), nullable=False)
    arguments_summary: Mapped[str] = mapped_column(Text, nullable=False)
    output_summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(128))


class MemoryClaim(Base):
    __tablename__ = "memory_claims"
    __table_args__ = (
        Index("ix_memory_claims_repository_status", "repository_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_ids_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    used_in_run: Mapped[str | None] = mapped_column(String(36))
    invalidated_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    __table_args__ = (
        Index("ix_evidence_records_run_source_type", "agent_run_id", "source_type"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(2048))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'low', 'medium', 'high', 'critical')",
            name="ck_findings_severity",
        ),
        Index("ix_findings_run_severity", "agent_run_id", "severity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    category: Mapped[str] = mapped_column(
        String(128), nullable=False, default="general"
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(2048))
    line_start: Mapped[int | None] = mapped_column(Integer)
    line_end: Mapped[int | None] = mapped_column(Integer)
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    symbol: Mapped[str | None] = mapped_column(String(1024))
    suggested_action: Mapped[str | None] = mapped_column(Text)
    verifier_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="needs_confirmation"
    )
    model_profile: Mapped[str | None] = mapped_column(String(255))
    evidence_ids_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class FixSession(Base):
    __tablename__ = "fix_sessions"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "repository_id",
            "pull_request_id",
            "finding_id",
            "head_sha",
            name="uq_fix_sessions_confirmation_binding",
        ),
        CheckConstraint(
            f"status IN ({_enum_sql(FixSessionStatus)})",
            name="ck_fix_sessions_status",
        ),
        CheckConstraint(
            f"permission_mode IN ({_enum_sql(FixPermissionMode)})",
            name="ck_fix_sessions_permission_mode",
        ),
        CheckConstraint(
            f"eligibility_status IS NULL OR eligibility_status IN ({_enum_sql(FixEligibilityStatus)})",
            name="ck_fix_sessions_eligibility_status",
        ),
        CheckConstraint(
            "cleanup_status IN ("
            + ", ".join(f"'{value}'" for value in FIX_WORKSPACE_CLEANUP_STATUSES)
            + ")",
            name="ck_fix_sessions_cleanup_status",
        ),
        CheckConstraint("lock_version >= 0", name="ck_fix_sessions_lock_version"),
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND latency_ms >= 0 AND retry_count >= 0",
            name="ck_fix_sessions_usage_nonnegative",
        ),
        CheckConstraint(
            "length(base_sha) >= 7 AND length(base_sha) <= 64 AND "
            "length(head_sha) >= 7 AND length(head_sha) <= 64",
            name="ck_fix_sessions_sha_lengths",
        ),
        Index("ix_fix_sessions_repository_status", "repository_id", "status"),
        Index("ix_fix_sessions_pr_created", "pull_request_id", "created_at"),
        Index("ix_fix_sessions_finding_created", "finding_id", "created_at"),
        Index("ix_fix_sessions_cleanup_activity", "cleanup_status", "last_active_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    pull_request_id: Mapped[str] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False
    )
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), nullable=False
    )
    source_agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    base_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    index_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("index_versions.id", ondelete="SET NULL")
    )
    workspace_index_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("index_versions.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(48), nullable=False, default=FixSessionStatus.CREATED.value
    )
    permission_mode: Mapped[str] = mapped_column(
        String(48), nullable=False, default=FixPermissionMode.PROPOSE_ONLY.value
    )
    eligibility_status: Mapped[str | None] = mapped_column(String(48))
    eligibility_reasons_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    eligibility_warnings_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    current_node: Mapped[str | None] = mapped_column(String(128))
    cancellation_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    plan_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    workspace_path: Mapped[str | None] = mapped_column(String(2048))
    workspace_state_hash: Mapped[str | None] = mapped_column(String(64))
    cleanup_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="NOT_CREATED"
    )
    model_profile: Mapped[str | None] = mapped_column(String(255))
    workflow_version: Mapped[str | None] = mapped_column(String(64))
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class PatchProposalRecord(Base):
    __tablename__ = "patch_proposals"
    __table_args__ = (
        UniqueConstraint(
            "fix_session_id",
            "proposal_version",
            name="uq_patch_proposals_session_version",
        ),
        UniqueConstraint(
            "fix_session_id", "patch_hash", name="uq_patch_proposals_session_hash"
        ),
        CheckConstraint("proposal_version >= 1", name="ck_patch_proposals_version"),
        CheckConstraint("changed_lines >= 0", name="ck_patch_proposals_changed_lines"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_patch_proposals_confidence"
        ),
        CheckConstraint(
            "length(patch_hash) = 64", name="ck_patch_proposals_hash_length"
        ),
        CheckConstraint(
            "length(base_sha) >= 7 AND length(base_sha) <= 64 AND "
            "length(head_sha) >= 7 AND length(head_sha) <= 64",
            name="ck_patch_proposals_sha_lengths",
        ),
        Index("ix_patch_proposals_session_created", "fix_session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    fix_session_id: Mapped[str] = mapped_column(
        ForeignKey("fix_sessions.id", ondelete="CASCADE"), nullable=False
    )
    proposal_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    base_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    patch: Mapped[str] = mapped_column(Text, nullable=False)
    patch_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    changed_files_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    changed_lines: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    validation_plan_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    assumptions_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    risk_notes_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    stale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FixConfirmation(Base):
    __tablename__ = "fix_confirmations"
    __table_args__ = (
        UniqueConstraint("nonce_hash", name="uq_fix_confirmations_nonce_hash"),
        ForeignKeyConstraint(
            [
                "fix_session_id",
                "repository_id",
                "pull_request_id",
                "finding_id",
                "head_sha",
            ],
            [
                "fix_sessions.id",
                "fix_sessions.repository_id",
                "fix_sessions.pull_request_id",
                "fix_sessions.finding_id",
                "fix_sessions.head_sha",
            ],
            ondelete="CASCADE",
            name="fk_fix_confirmations_session_binding",
        ),
        CheckConstraint(
            "length(patch_hash) = 64", name="ck_fix_confirmations_patch_hash"
        ),
        CheckConstraint(
            "length(nonce_hash) = 64", name="ck_fix_confirmations_nonce_hash"
        ),
        CheckConstraint(
            "length(head_sha) >= 7 AND length(head_sha) <= 64",
            name="ck_fix_confirmations_head_sha_length",
        ),
        CheckConstraint(
            "consumed_at IS NULL OR confirmed_at IS NOT NULL",
            name="ck_fix_confirmations_consumed_after_confirmed",
        ),
        Index("ix_fix_confirmations_session_expires", "fix_session_id", "expires_at"),
        Index(
            "ix_fix_confirmations_binding",
            "repository_id",
            "pull_request_id",
            "finding_id",
            "head_sha",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    fix_session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    pull_request_id: Mapped[str] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False
    )
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), nullable=False
    )
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    patch_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class ValidationRun(Base):
    __tablename__ = "validation_runs"
    __table_args__ = (
        UniqueConstraint(
            "fix_session_id", "sequence", name="uq_validation_runs_session_sequence"
        ),
        CheckConstraint("sequence >= 1", name="ck_validation_runs_sequence"),
        CheckConstraint(
            f"status IN ({_enum_sql(ValidationStatus)})",
            name="ck_validation_runs_status",
        ),
        CheckConstraint(
            "return_code IS NULL OR return_code >= 0",
            name="ck_validation_runs_return_code",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_validation_runs_duration",
        ),
        Index("ix_validation_runs_session_status", "fix_session_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    fix_session_id: Mapped[str] = mapped_column(
        ForeignKey("fix_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    command: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=ValidationStatus.QUEUED.value
    )
    return_code: Mapped[int | None] = mapped_column(Integer)
    stdout_summary: Mapped[str | None] = mapped_column(Text)
    stderr_summary: Mapped[str | None] = mapped_column(Text)
    output_truncated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    error_code: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class FixResult(Base):
    __tablename__ = "fix_results"
    __table_args__ = (
        UniqueConstraint("fix_session_id", name="uq_fix_results_fix_session_id"),
        CheckConstraint(
            f"resolution IN ({_enum_sql(FixResolution)})",
            name="ck_fix_results_resolution",
        ),
        CheckConstraint(
            f"validation_status IS NULL OR validation_status IN ({_enum_sql(ValidationStatus)})",
            name="ck_fix_results_validation_status",
        ),
        Index("ix_fix_results_resolution_created", "resolution", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    fix_session_id: Mapped[str] = mapped_column(
        ForeignKey("fix_sessions.id", ondelete="CASCADE"), nullable=False
    )
    resolution: Mapped[str] = mapped_column(String(40), nullable=False)
    validation_status: Mapped[str | None] = mapped_column(String(40))
    re_review_status: Mapped[str] = mapped_column(String(128), nullable=False)
    residual_findings_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    residual_risks_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    report_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class FixStep(Base):
    __tablename__ = "fix_steps"
    __table_args__ = (
        UniqueConstraint(
            "fix_session_id", "sequence", name="uq_fix_steps_session_sequence"
        ),
        CheckConstraint("sequence >= 1", name="ck_fix_steps_sequence"),
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_fix_steps_status",
        ),
        Index("ix_fix_steps_session_status", "fix_session_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    fix_session_id: Mapped[str] = mapped_column(
        ForeignKey("fix_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    node: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    input_summary: Mapped[str | None] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class FixToolCallRecord(Base):
    __tablename__ = "fix_tool_calls"
    __table_args__ = (
        CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_fix_tool_calls_status",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0", name="ck_fix_tool_calls_duration"
        ),
        Index("ix_fix_tool_calls_step_tool", "fix_step_id", "tool_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    fix_step_id: Mapped[str] = mapped_column(
        ForeignKey("fix_steps.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    permission: Mapped[str] = mapped_column(String(64), nullable=False)
    arguments_summary: Mapped[str] = mapped_column(Text, nullable=False)
    output_summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(128))


class FixEvent(Base):
    __tablename__ = "fix_events"
    __table_args__ = (
        UniqueConstraint(
            "fix_session_id", "sequence", name="uq_fix_events_session_sequence"
        ),
        CheckConstraint("sequence >= 1", name="ck_fix_events_sequence"),
        Index("ix_fix_events_session_created", "fix_session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    fix_session_id: Mapped[str] = mapped_column(
        ForeignKey("fix_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class EvalRun(Base):
    __tablename__ = "eval_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_eval_runs_status",
        ),
        Index("ix_eval_runs_benchmark_created_at", "benchmark", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    benchmark: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String(128))
    model_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint("delivery_id", name="uq_webhook_deliveries_delivery_id"),
        Index("ix_webhook_deliveries_received", "received_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    delivery_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    repository_full_name: Mapped[str | None] = mapped_column(String(201))
    pull_request_number: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationRecord(Base):
    __tablename__ = "notification_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('delivered', 'failed')",
            name="ck_notification_records_status",
        ),
        Index("ix_notification_records_kind_attempted", "kind", "attempted_at"),
        Index("ix_notification_records_status_attempted", "status", "attempted_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    deep_link: Mapped[str | None] = mapped_column(String(2048))
    repository_id: Mapped[str | None] = mapped_column(
        ForeignKey("repositories.id", ondelete="SET NULL")
    )
    pull_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="SET NULL")
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
