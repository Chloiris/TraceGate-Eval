"""Create the initial TraceGate Studio schema.

Revision ID: 20260710_0001
Revises: None
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260710_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("theme", sa.String(length=16), server_default="system", nullable=False),
        sa.Column("language", sa.String(length=16), server_default="zh-CN", nullable=False),
        sa.Column("background_monitoring", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("launch_at_startup", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("model_provider", sa.String(length=64), nullable=True),
        sa.Column("model_base_url", sa.String(length=2048), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_app_settings_singleton"),
        sa.CheckConstraint("theme IN ('system', 'light', 'dark')", name="ck_app_settings_theme"),
        sa.CheckConstraint("language IN ('zh-CN', 'en-US')", name="ck_app_settings_language"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(
        sa.table(
            "app_settings",
            sa.column("id", sa.Integer()),
            sa.column("theme", sa.String()),
            sa.column("language", sa.String()),
            sa.column("background_monitoring", sa.Boolean()),
            sa.column("launch_at_startup", sa.Boolean()),
        ),
        [
            {
                "id": 1,
                "theme": "system",
                "language": "zh-CN",
                "background_monitoring": False,
                "launch_at_startup": False,
            }
        ],
    )

    op.create_table(
        "onboarding_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("current_step", sa.String(length=32), server_default="welcome", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_onboarding_state_singleton"),
        sa.CheckConstraint(
            "current_step IN ('welcome', 'appearance', 'github', 'model', 'repository', 'background', 'complete')",
            name="ck_onboarding_state_step",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(
        sa.table(
            "onboarding_state",
            sa.column("id", sa.Integer()),
            sa.column("completed", sa.Boolean()),
            sa.column("current_step", sa.String()),
        ),
        [{"id": 1, "completed": False, "current_step": "welcome"}],
    )

    op.create_table(
        "repositories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=201), nullable=False),
        sa.Column("clone_url", sa.String(length=2048), nullable=True),
        sa.Column("local_path", sa.String(length=2048), nullable=True),
        sa.Column("default_branch", sa.String(length=255), nullable=True),
        sa.Column("monitoring_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("connection_status", sa.String(length=32), server_default="not_connected", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint(
            "connection_status IN ('not_connected', 'pending', 'ready', 'error')",
            name="ck_repositories_connection_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("full_name", name="uq_repositories_full_name"),
    )
    op.create_index("ix_repositories_monitoring_enabled", "repositories", ["monitoring_enabled"])

    op.create_table(
        "pull_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("base_sha", sa.String(length=64), nullable=True),
        sa.Column("head_sha", sa.String(length=64), nullable=True),
        sa.Column("updated_at_github", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "number", name="uq_pull_requests_repository_number"),
    )
    op.create_index("ix_pull_requests_repository_state", "pull_requests", ["repository_id", "state"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("pull_request_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("current_node", sa.String(length=128), nullable=True),
        sa.Column("head_sha", sa.String(length=64), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("index_version", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_agent_runs_status",
        ),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_repository_status", "agent_runs", ["repository_id", "status"])

    op.create_table(
        "evidence_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("agent_run_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.String(length=2048), nullable=False),
        sa.Column("file_path", sa.String(length=2048), nullable=True),
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evidence_records_run_source_type", "evidence_records", ["agent_run_id", "source_type"]
    )

    op.create_table(
        "findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_run_id", sa.String(length=36), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(length=2048), nullable=True),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('info', 'low', 'medium', 'high', 'critical')",
            name="ck_findings_severity",
        ),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_findings_run_severity", "findings", ["agent_run_id", "severity"])

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("benchmark", sa.String(length=128), nullable=False),
        sa.Column("dataset_version", sa.String(length=128), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')", name="ck_eval_runs_status"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_runs_benchmark_created_at", "eval_runs", ["benchmark", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_eval_runs_benchmark_created_at", table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_index("ix_findings_run_severity", table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_evidence_records_run_source_type", table_name="evidence_records")
    op.drop_table("evidence_records")
    op.drop_index("ix_agent_runs_repository_status", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_pull_requests_repository_state", table_name="pull_requests")
    op.drop_table("pull_requests")
    op.drop_index("ix_repositories_monitoring_enabled", table_name="repositories")
    op.drop_table("repositories")
    op.drop_table("onboarding_state")
    op.drop_table("app_settings")
