"""Persist desktop UX and configurable runtime preferences.

Revision ID: 20260710_0004
Revises: 20260710_0003
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260710_0004"
down_revision: str | None = "20260710_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_array_default = (
        sa.text("(JSON_ARRAY())")
        if op.get_bind().dialect.name == "mysql"
        else sa.text("'[]'")
    )
    op.add_column(
        "app_settings",
        sa.Column("close_notice_dismissed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("notifications_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("model_temperature", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("model_max_output_tokens", sa.Integer(), server_default="4096", nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("model_timeout_seconds", sa.Integer(), server_default="60", nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("model_max_retries", sa.Integer(), server_default="2", nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("model_native_structured_output", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("model_streaming_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("model_native_tool_calling", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("model_context_scope", sa.String(length=32), server_default="changed_files", nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("model_input_cost_per_million", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("model_output_cost_per_million", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("github_poll_interval_seconds", sa.Integer(), server_default="60", nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("automatic_analysis_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("automatic_analysis_include_drafts", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("automatic_analysis_require_checks_success", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("analysis_paused", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("webhook_relay_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("webhook_relay_device_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("disabled_agents_json", sa.JSON(), server_default=json_array_default, nullable=False),
    )
    op.add_column(
        "app_settings",
        sa.Column("disabled_tools_json", sa.JSON(), server_default=json_array_default, nullable=False),
    )
    op.add_column("pull_requests", sa.Column("checks_etag", sa.String(length=512), nullable=True))
    op.add_column("pull_requests", sa.Column("base_ref", sa.String(length=255), nullable=True))
    op.add_column("pull_requests", sa.Column("head_ref", sa.String(length=255), nullable=True))
    op.add_column(
        "pull_requests",
        sa.Column("checks_status", sa.String(length=32), server_default="not_available", nullable=False),
    )
    op.add_column(
        "pull_requests",
        sa.Column("last_checks_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("pull_requests", sa.Column("risk_level", sa.String(length=16), nullable=True))
    op.add_column("pull_requests", sa.Column("risk_score", sa.Float(), nullable=True))
    op.add_column("pull_requests", sa.Column("conclusion_summary", sa.Text(), nullable=True))
    op.add_column(
        "pull_requests",
        sa.Column("impact_paths_json", sa.JSON(), server_default=json_array_default, nullable=False),
    )
    op.add_column(
        "pull_requests",
        sa.Column("recommended_review_order_json", sa.JSON(), server_default=json_array_default, nullable=False),
    )
    op.add_column(
        "pull_requests",
        sa.Column("latest_model_profile", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "repository_syncs",
        sa.Column("checks_changed_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "repository_syncs",
        sa.Column("github_api_request_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "repository_syncs",
        sa.Column("github_api_duration_ms", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "agent_runs",
        sa.Column("context_scope", sa.String(length=32), server_default="changed_files", nullable=False),
    )
    op.add_column(
        "agent_runs",
        sa.Column("retrieval_hit_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "index_versions",
        sa.Column("index_duration_ms", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "index_versions",
        sa.Column("graph_duration_ms", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "model_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("profile_label", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("native_structured_output", sa.Boolean(), nullable=False),
        sa.Column("streaming_enabled", sa.Boolean(), nullable=False),
        sa.Column("native_tool_calling", sa.Boolean(), nullable=False),
        sa.Column("context_scope", sa.String(length=32), nullable=False),
        sa.Column("input_cost_per_million", sa.Float(), server_default="0", nullable=False),
        sa.Column("output_cost_per_million", sa.Float(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", name="uq_model_profiles_fingerprint"),
    )
    op.create_index(
        "ix_model_profiles_provider_model", "model_profiles", ["provider", "model_name"]
    )
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.add_column(sa.Column("model_profile_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_agent_runs_model_profile_id",
            "model_profiles",
            ["model_profile_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_table(
        "commits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pull_request_id", sa.String(length=36), nullable=False),
        sa.Column("sha", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("author_email", sa.String(length=320), nullable=True),
        sa.Column("author_login", sa.String(length=255), nullable=True),
        sa.Column("authored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("html_url", sa.String(length=2048), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pull_request_id", "sha", name="uq_commits_pr_sha"),
    )
    op.create_index("ix_commits_pr_position", "commits", ["pull_request_id", "position"])
    op.create_table(
        "changed_files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pull_request_id", sa.String(length=36), nullable=False),
        sa.Column("head_sha", sa.String(length=64), nullable=False),
        sa.Column("blob_sha", sa.String(length=64), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("previous_path", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("additions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deletions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("changes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("blob_url", sa.String(length=2048), nullable=True),
        sa.Column("raw_url", sa.String(length=2048), nullable=True),
        sa.Column("contents_url", sa.String(length=2048), nullable=True),
        sa.Column("patch", sa.Text(), nullable=True),
        sa.Column("patch_hash", sa.String(length=64), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pull_request_id", "head_sha", "path", name="uq_changed_files_pr_head_path"),
    )
    op.create_index("ix_changed_files_pr_head", "changed_files", ["pull_request_id", "head_sha"])
    op.create_table(
        "changed_hunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("changed_file_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("header", sa.String(length=1024), nullable=False),
        sa.Column("old_start", sa.Integer(), nullable=False),
        sa.Column("old_count", sa.Integer(), nullable=False),
        sa.Column("new_start", sa.Integer(), nullable=False),
        sa.Column("new_count", sa.Integer(), nullable=False),
        sa.Column("patch", sa.Text(), nullable=False),
        sa.Column("patch_hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["changed_file_id"], ["changed_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("changed_file_id", "sequence", name="uq_changed_hunks_file_sequence"),
    )
    op.create_index("ix_changed_hunks_file_new_start", "changed_hunks", ["changed_file_id", "new_start"])
    op.create_table(
        "check_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pull_request_id", sa.String(length=36), nullable=False),
        sa.Column("github_id", sa.Integer(), nullable=False),
        sa.Column("head_sha", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("conclusion", sa.String(length=64), nullable=True),
        sa.Column("details_url", sa.String(length=2048), nullable=True),
        sa.Column("app_name", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pull_request_id", "github_id", name="uq_check_runs_pr_github_id"),
    )
    op.create_index("ix_check_runs_pr_status", "check_runs", ["pull_request_id", "status"])
    op.create_table(
        "notification_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("deep_link", sa.String(length=2048), nullable=True),
        sa.Column("repository_id", sa.String(length=36), nullable=True),
        sa.Column("pull_request_id", sa.String(length=36), nullable=True),
        sa.Column("agent_run_id", sa.String(length=36), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("status IN ('delivered', 'failed')", name="ck_notification_records_status"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_records_kind_attempted", "notification_records", ["kind", "attempted_at"]
    )
    op.create_index(
        "ix_notification_records_status_attempted", "notification_records", ["status", "attempted_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_notification_records_status_attempted", table_name="notification_records")
    op.drop_index("ix_notification_records_kind_attempted", table_name="notification_records")
    op.drop_table("notification_records")
    op.drop_index("ix_check_runs_pr_status", table_name="check_runs")
    op.drop_table("check_runs")
    op.drop_index("ix_changed_hunks_file_new_start", table_name="changed_hunks")
    op.drop_table("changed_hunks")
    op.drop_index("ix_changed_files_pr_head", table_name="changed_files")
    op.drop_table("changed_files")
    op.drop_index("ix_commits_pr_position", table_name="commits")
    op.drop_table("commits")
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.drop_constraint("fk_agent_runs_model_profile_id", type_="foreignkey")
        batch_op.drop_column("model_profile_id")
    op.drop_index("ix_model_profiles_provider_model", table_name="model_profiles")
    op.drop_table("model_profiles")
    op.drop_column("index_versions", "graph_duration_ms")
    op.drop_column("index_versions", "index_duration_ms")
    op.drop_column("agent_runs", "retrieval_hit_count")
    op.drop_column("agent_runs", "context_scope")
    op.drop_column("repository_syncs", "github_api_duration_ms")
    op.drop_column("repository_syncs", "github_api_request_count")
    op.drop_column("repository_syncs", "checks_changed_count")
    op.drop_column("pull_requests", "latest_model_profile")
    op.drop_column("pull_requests", "recommended_review_order_json")
    op.drop_column("pull_requests", "impact_paths_json")
    op.drop_column("pull_requests", "conclusion_summary")
    op.drop_column("pull_requests", "risk_score")
    op.drop_column("pull_requests", "risk_level")
    op.drop_column("pull_requests", "last_checks_synced_at")
    op.drop_column("pull_requests", "checks_status")
    op.drop_column("pull_requests", "head_ref")
    op.drop_column("pull_requests", "base_ref")
    op.drop_column("pull_requests", "checks_etag")
    op.drop_column("app_settings", "disabled_tools_json")
    op.drop_column("app_settings", "disabled_agents_json")
    op.drop_column("app_settings", "webhook_relay_device_id")
    op.drop_column("app_settings", "webhook_relay_url")
    op.drop_column("app_settings", "analysis_paused")
    op.drop_column("app_settings", "automatic_analysis_require_checks_success")
    op.drop_column("app_settings", "automatic_analysis_include_drafts")
    op.drop_column("app_settings", "automatic_analysis_enabled")
    op.drop_column("app_settings", "github_poll_interval_seconds")
    op.drop_column("app_settings", "model_output_cost_per_million")
    op.drop_column("app_settings", "model_input_cost_per_million")
    op.drop_column("app_settings", "model_context_scope")
    op.drop_column("app_settings", "model_native_tool_calling")
    op.drop_column("app_settings", "model_streaming_enabled")
    op.drop_column("app_settings", "model_native_structured_output")
    op.drop_column("app_settings", "model_max_retries")
    op.drop_column("app_settings", "model_timeout_seconds")
    op.drop_column("app_settings", "model_max_output_tokens")
    op.drop_column("app_settings", "model_temperature")
    op.drop_column("app_settings", "notifications_enabled")
    op.drop_column("app_settings", "close_notice_dismissed")
