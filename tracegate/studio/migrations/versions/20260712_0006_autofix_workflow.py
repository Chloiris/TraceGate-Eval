"""Persist the controlled coding-agent autofix workflow.

Revision ID: 20260712_0006
Revises: 20260711_0005
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260712_0006"
down_revision: str | None = "20260711_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FIX_SESSION_STATUSES = (
    "CREATED",
    "CHECKING_ELIGIBILITY",
    "ELIGIBLE",
    "PLANNING",
    "PLAN_READY",
    "GENERATING_PATCH",
    "VALIDATING_PATCH",
    "AWAITING_USER_CONFIRMATION",
    "APPLYING_PATCH",
    "PATCH_APPLIED",
    "RUNNING_VALIDATION",
    "VALIDATION_COMPLETE",
    "REINDEXING_CHANGES",
    "RE_REVIEWING",
    "FINALIZING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "ROLLED_BACK",
    "STALE",
)
FIX_PERMISSION_MODES = ("PROPOSE_ONLY", "APPLY_IN_ISOLATED_WORKSPACE")
FIX_ELIGIBILITY_STATUSES = (
    "ELIGIBLE",
    "NEEDS_CONFIRMATION",
    "INSUFFICIENT_EVIDENCE",
    "STALE_HEAD",
    "UNSUPPORTED_FILE",
    "SENSITIVE_PATH",
    "BLOCKED",
)
VALIDATION_STATUSES = (
    "QUEUED",
    "RUNNING",
    "PASSED",
    "FAILED",
    "CANCELLED",
    "NO_TEST_COMMAND_AVAILABLE",
)
FIX_RESOLUTIONS = (
    "RESOLVED",
    "PARTIALLY_RESOLVED",
    "NOT_RESOLVED",
    "VERIFICATION_FAILED",
    "NEEDS_HUMAN_REVIEW",
)
FIX_WORKSPACE_CLEANUP_STATUSES = (
    "NOT_CREATED",
    "ACTIVE",
    "CLEANUP_PENDING",
    "DELETED",
    "CLEANUP_FAILED",
    "RETAINED",
)


def _in_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    json_array_default = (
        sa.text("(JSON_ARRAY())") if dialect == "mysql" else sa.text("'[]'")
    )
    json_object_default = (
        sa.text("(JSON_OBJECT())") if dialect == "mysql" else sa.text("'{}'")
    )

    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "autofix_max_files", sa.Integer(), server_default="8", nullable=False
            )
        )
        batch_op.add_column(
            sa.Column(
                "autofix_max_changed_lines",
                sa.Integer(),
                server_default="800",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "autofix_confirmation_ttl_seconds",
                sa.Integer(),
                server_default="900",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "autofix_workspace_retention_hours",
                sa.Integer(),
                server_default="24",
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "ck_app_settings_autofix_max_files",
            "autofix_max_files >= 1 AND autofix_max_files <= 32",
        )
        batch_op.create_check_constraint(
            "ck_app_settings_autofix_max_changed_lines",
            "autofix_max_changed_lines >= 50 AND autofix_max_changed_lines <= 5000",
        )
        batch_op.create_check_constraint(
            "ck_app_settings_autofix_confirmation_ttl_seconds",
            "autofix_confirmation_ttl_seconds >= 60 "
            "AND autofix_confirmation_ttl_seconds <= 3600",
        )
        batch_op.create_check_constraint(
            "ck_app_settings_autofix_workspace_retention_hours",
            "autofix_workspace_retention_hours >= 1 "
            "AND autofix_workspace_retention_hours <= 168",
        )

    op.create_table(
        "fix_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("pull_request_id", sa.String(36), nullable=False),
        sa.Column("finding_id", sa.String(36), nullable=False),
        sa.Column("source_agent_run_id", sa.String(36), nullable=False),
        sa.Column("base_sha", sa.String(64), nullable=False),
        sa.Column("head_sha", sa.String(64), nullable=False),
        sa.Column("index_version_id", sa.String(36), nullable=True),
        sa.Column("workspace_index_version_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(48), server_default="CREATED", nullable=False),
        sa.Column(
            "permission_mode",
            sa.String(48),
            server_default="PROPOSE_ONLY",
            nullable=False,
        ),
        sa.Column("eligibility_status", sa.String(48), nullable=True),
        sa.Column(
            "eligibility_reasons_json",
            sa.JSON(),
            server_default=json_array_default,
            nullable=False,
        ),
        sa.Column(
            "eligibility_warnings_json",
            sa.JSON(),
            server_default=json_array_default,
            nullable=False,
        ),
        sa.Column("current_node", sa.String(128), nullable=True),
        sa.Column(
            "cancellation_requested",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("lock_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("plan_json", sa.JSON(), nullable=True),
        sa.Column("workspace_path", sa.String(2048), nullable=True),
        sa.Column("workspace_state_hash", sa.String(64), nullable=True),
        sa.Column(
            "cleanup_status",
            sa.String(32),
            server_default="NOT_CREATED",
            nullable=False,
        ),
        sa.Column("model_profile", sa.String(255), nullable=True),
        sa.Column("workflow_version", sa.String(64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"status IN ({_in_values(FIX_SESSION_STATUSES)})",
            name="ck_fix_sessions_status",
        ),
        sa.CheckConstraint(
            f"permission_mode IN ({_in_values(FIX_PERMISSION_MODES)})",
            name="ck_fix_sessions_permission_mode",
        ),
        sa.CheckConstraint(
            "eligibility_status IS NULL OR eligibility_status IN "
            f"({_in_values(FIX_ELIGIBILITY_STATUSES)})",
            name="ck_fix_sessions_eligibility_status",
        ),
        sa.CheckConstraint(
            f"cleanup_status IN ({_in_values(FIX_WORKSPACE_CLEANUP_STATUSES)})",
            name="ck_fix_sessions_cleanup_status",
        ),
        sa.CheckConstraint("lock_version >= 0", name="ck_fix_sessions_lock_version"),
        sa.CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 "
            "AND latency_ms >= 0 AND retry_count >= 0",
            name="ck_fix_sessions_usage_nonnegative",
        ),
        sa.CheckConstraint(
            "length(base_sha) >= 7 AND length(base_sha) <= 64 "
            "AND length(head_sha) >= 7 AND length(head_sha) <= 64",
            name="ck_fix_sessions_sha_lengths",
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"], ["repositories.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pull_request_id"], ["pull_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["index_version_id"], ["index_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_index_version_id"],
            ["index_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "repository_id",
            "pull_request_id",
            "finding_id",
            "head_sha",
            name="uq_fix_sessions_confirmation_binding",
        ),
    )
    op.create_index(
        "ix_fix_sessions_repository_status",
        "fix_sessions",
        ["repository_id", "status"],
    )
    op.create_index(
        "ix_fix_sessions_pr_created",
        "fix_sessions",
        ["pull_request_id", "created_at"],
    )
    op.create_index(
        "ix_fix_sessions_finding_created",
        "fix_sessions",
        ["finding_id", "created_at"],
    )
    op.create_index(
        "ix_fix_sessions_cleanup_activity",
        "fix_sessions",
        ["cleanup_status", "last_active_at"],
    )

    op.create_table(
        "patch_proposals",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("fix_session_id", sa.String(36), nullable=False),
        sa.Column("proposal_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("base_sha", sa.String(64), nullable=False),
        sa.Column("head_sha", sa.String(64), nullable=False),
        sa.Column("patch", sa.Text(), nullable=False),
        sa.Column("patch_hash", sa.String(64), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "changed_files_json",
            sa.JSON(),
            server_default=json_array_default,
            nullable=False,
        ),
        sa.Column("changed_lines", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "validation_plan_json",
            sa.JSON(),
            server_default=json_object_default,
            nullable=False,
        ),
        sa.Column(
            "assumptions_json",
            sa.JSON(),
            server_default=json_array_default,
            nullable=False,
        ),
        sa.Column(
            "risk_notes_json",
            sa.JSON(),
            server_default=json_array_default,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("proposal_version >= 1", name="ck_patch_proposals_version"),
        sa.CheckConstraint(
            "changed_lines >= 0", name="ck_patch_proposals_changed_lines"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_patch_proposals_confidence",
        ),
        sa.CheckConstraint(
            "length(patch_hash) = 64", name="ck_patch_proposals_hash_length"
        ),
        sa.CheckConstraint(
            "length(base_sha) >= 7 AND length(base_sha) <= 64 "
            "AND length(head_sha) >= 7 AND length(head_sha) <= 64",
            name="ck_patch_proposals_sha_lengths",
        ),
        sa.ForeignKeyConstraint(
            ["fix_session_id"], ["fix_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fix_session_id",
            "proposal_version",
            name="uq_patch_proposals_session_version",
        ),
        sa.UniqueConstraint(
            "fix_session_id", "patch_hash", name="uq_patch_proposals_session_hash"
        ),
    )
    op.create_index(
        "ix_patch_proposals_session_created",
        "patch_proposals",
        ["fix_session_id", "created_at"],
    )

    op.create_table(
        "fix_confirmations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("fix_session_id", sa.String(36), nullable=False),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("pull_request_id", sa.String(36), nullable=False),
        sa.Column("finding_id", sa.String(36), nullable=False),
        sa.Column("head_sha", sa.String(64), nullable=False),
        sa.Column("patch_hash", sa.String(64), nullable=False),
        sa.Column("nonce_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(patch_hash) = 64", name="ck_fix_confirmations_patch_hash"
        ),
        sa.CheckConstraint(
            "length(nonce_hash) = 64", name="ck_fix_confirmations_nonce_hash"
        ),
        sa.CheckConstraint(
            "length(head_sha) >= 7 AND length(head_sha) <= 64",
            name="ck_fix_confirmations_head_sha_length",
        ),
        sa.CheckConstraint(
            "consumed_at IS NULL OR confirmed_at IS NOT NULL",
            name="ck_fix_confirmations_consumed_after_confirmed",
        ),
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
            ["repository_id"], ["repositories.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pull_request_id"], ["pull_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nonce_hash", name="uq_fix_confirmations_nonce_hash"),
    )
    op.create_index(
        "ix_fix_confirmations_session_expires",
        "fix_confirmations",
        ["fix_session_id", "expires_at"],
    )
    op.create_index(
        "ix_fix_confirmations_binding",
        "fix_confirmations",
        ["repository_id", "pull_request_id", "finding_id", "head_sha"],
    )

    op.create_table(
        "validation_runs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("fix_session_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "command", sa.JSON(), server_default=json_array_default, nullable=False
        ),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("status", sa.String(40), server_default="QUEUED", nullable=False),
        sa.Column("return_code", sa.Integer(), nullable=True),
        sa.Column("stdout_summary", sa.Text(), nullable=True),
        sa.Column("stderr_summary", sa.Text(), nullable=True),
        sa.Column(
            "output_truncated", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_validation_runs_sequence"),
        sa.CheckConstraint(
            f"status IN ({_in_values(VALIDATION_STATUSES)})",
            name="ck_validation_runs_status",
        ),
        sa.CheckConstraint(
            "return_code IS NULL OR return_code >= 0",
            name="ck_validation_runs_return_code",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_validation_runs_duration",
        ),
        sa.ForeignKeyConstraint(
            ["fix_session_id"], ["fix_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fix_session_id", "sequence", name="uq_validation_runs_session_sequence"
        ),
    )
    op.create_index(
        "ix_validation_runs_session_status",
        "validation_runs",
        ["fix_session_id", "status"],
    )

    op.create_table(
        "fix_results",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("fix_session_id", sa.String(36), nullable=False),
        sa.Column("resolution", sa.String(40), nullable=False),
        sa.Column("validation_status", sa.String(40), nullable=True),
        sa.Column("re_review_status", sa.String(128), nullable=False),
        sa.Column(
            "residual_findings_json",
            sa.JSON(),
            server_default=json_array_default,
            nullable=False,
        ),
        sa.Column(
            "residual_risks_json",
            sa.JSON(),
            server_default=json_array_default,
            nullable=False,
        ),
        sa.Column(
            "report_json", sa.JSON(), server_default=json_object_default, nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"resolution IN ({_in_values(FIX_RESOLUTIONS)})",
            name="ck_fix_results_resolution",
        ),
        sa.CheckConstraint(
            "validation_status IS NULL OR validation_status IN "
            f"({_in_values(VALIDATION_STATUSES)})",
            name="ck_fix_results_validation_status",
        ),
        sa.ForeignKeyConstraint(
            ["fix_session_id"], ["fix_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fix_session_id", name="uq_fix_results_fix_session_id"),
    )
    op.create_index(
        "ix_fix_results_resolution_created",
        "fix_results",
        ["resolution", "created_at"],
    )

    op.create_table(
        "fix_steps",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("fix_session_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("node", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), server_default="QUEUED", nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.CheckConstraint("sequence >= 1", name="ck_fix_steps_sequence"),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_fix_steps_status",
        ),
        sa.ForeignKeyConstraint(
            ["fix_session_id"], ["fix_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fix_session_id", "sequence", name="uq_fix_steps_session_sequence"
        ),
    )
    op.create_index(
        "ix_fix_steps_session_status",
        "fix_steps",
        ["fix_session_id", "status"],
    )

    op.create_table(
        "fix_tool_calls",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("fix_step_id", sa.String(36), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("permission", sa.String(64), nullable=False),
        sa.Column("arguments_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_fix_tool_calls_status",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_fix_tool_calls_duration",
        ),
        sa.ForeignKeyConstraint(["fix_step_id"], ["fix_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fix_tool_calls_step_tool",
        "fix_tool_calls",
        ["fix_step_id", "tool_name"],
    )

    op.create_table(
        "fix_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("fix_session_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column(
            "payload_json",
            sa.JSON(),
            server_default=json_object_default,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_fix_events_sequence"),
        sa.ForeignKeyConstraint(
            ["fix_session_id"], ["fix_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fix_session_id", "sequence", name="uq_fix_events_session_sequence"
        ),
    )
    op.create_index(
        "ix_fix_events_session_created",
        "fix_events",
        ["fix_session_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_fix_events_session_created", table_name="fix_events")
    op.drop_table("fix_events")
    op.drop_index("ix_fix_tool_calls_step_tool", table_name="fix_tool_calls")
    op.drop_table("fix_tool_calls")
    op.drop_index("ix_fix_steps_session_status", table_name="fix_steps")
    op.drop_table("fix_steps")
    op.drop_index("ix_fix_results_resolution_created", table_name="fix_results")
    op.drop_table("fix_results")
    op.drop_index("ix_validation_runs_session_status", table_name="validation_runs")
    op.drop_table("validation_runs")
    op.drop_index("ix_fix_confirmations_binding", table_name="fix_confirmations")
    op.drop_index(
        "ix_fix_confirmations_session_expires", table_name="fix_confirmations"
    )
    op.drop_table("fix_confirmations")
    op.drop_index("ix_patch_proposals_session_created", table_name="patch_proposals")
    op.drop_table("patch_proposals")
    op.drop_index("ix_fix_sessions_cleanup_activity", table_name="fix_sessions")
    op.drop_index("ix_fix_sessions_finding_created", table_name="fix_sessions")
    op.drop_index("ix_fix_sessions_pr_created", table_name="fix_sessions")
    op.drop_index("ix_fix_sessions_repository_status", table_name="fix_sessions")
    op.drop_table("fix_sessions")

    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.drop_constraint(
            "ck_app_settings_autofix_workspace_retention_hours", type_="check"
        )
        batch_op.drop_constraint(
            "ck_app_settings_autofix_confirmation_ttl_seconds", type_="check"
        )
        batch_op.drop_constraint(
            "ck_app_settings_autofix_max_changed_lines", type_="check"
        )
        batch_op.drop_constraint("ck_app_settings_autofix_max_files", type_="check")
        batch_op.drop_column("autofix_workspace_retention_hours")
        batch_op.drop_column("autofix_confirmation_ttl_seconds")
        batch_op.drop_column("autofix_max_changed_lines")
        batch_op.drop_column("autofix_max_files")
