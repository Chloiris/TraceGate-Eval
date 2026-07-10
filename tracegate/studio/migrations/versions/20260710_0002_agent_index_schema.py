"""Add commit-bound indexing, polling, trace, graph, and memory records.

Revision ID: 20260710_0002
Revises: 20260710_0001
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260710_0002"
down_revision: str | None = "20260710_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column("current_commit_sha", sa.String(64), nullable=True))
    op.add_column("repositories", sa.Column("current_index_version", sa.String(36), nullable=True))
    op.add_column("repositories", sa.Column("sync_etag", sa.String(512), nullable=True))
    op.add_column("repositories", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("repositories", sa.Column("github_rate_remaining", sa.Integer(), nullable=True))
    op.add_column("pull_requests", sa.Column("draft", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("pull_requests", sa.Column("additions", sa.Integer(), server_default="0", nullable=False))
    op.add_column("pull_requests", sa.Column("deletions", sa.Integer(), server_default="0", nullable=False))
    op.add_column("pull_requests", sa.Column("changed_files", sa.Integer(), server_default="0", nullable=False))
    op.add_column("pull_requests", sa.Column("analysis_status", sa.String(32), server_default="not_analyzed", nullable=False))
    op.add_column("agent_runs", sa.Column("workflow_version", sa.String(64), nullable=True))
    op.add_column("agent_runs", sa.Column("model_profile", sa.String(255), nullable=True))
    op.add_column("agent_runs", sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False))
    op.add_column("agent_runs", sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False))
    op.add_column("agent_runs", sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False))
    op.add_column("agent_runs", sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("agent_runs", sa.Column("cancellation_requested", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("findings", sa.Column("confidence", sa.Float(), server_default="0", nullable=False))
    op.add_column("findings", sa.Column("category", sa.String(128), server_default="general", nullable=False))
    op.add_column("findings", sa.Column("commit_sha", sa.String(64), nullable=True))
    op.add_column("findings", sa.Column("symbol", sa.String(1024), nullable=True))
    op.add_column("findings", sa.Column("suggested_action", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("verifier_status", sa.String(64), server_default="needs_confirmation", nullable=False))
    op.add_column("findings", sa.Column("model_profile", sa.String(255), nullable=True))

    op.create_table(
        "repository_syncs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("etag", sa.String(512), nullable=True),
        sa.Column("commit_sha", sa.String(64), nullable=True),
        sa.Column("changed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repository_syncs_repository_started", "repository_syncs", ["repository_id", "started_at"])

    op.create_table(
        "pull_request_snapshots",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("pull_request_id", sa.String(36), nullable=False),
        sa.Column("base_sha", sa.String(64), nullable=False),
        sa.Column("head_sha", sa.String(64), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pull_request_id", "head_sha", "payload_hash", name="uq_pr_snapshot_head_payload"),
    )
    op.create_index("ix_pr_snapshots_pr_captured", "pull_request_snapshots", ["pull_request_id", "captured_at"])

    op.create_table(
        "index_versions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("symbol_count", sa.Integer(), nullable=False),
        sa.Column("changed_count", sa.Integer(), nullable=False),
        sa.Column("deleted_count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "commit_sha", name="uq_index_repository_commit"),
    )
    op.create_index("ix_index_versions_repository_created", "index_versions", ["repository_id", "created_at"])

    op.create_table(
        "indexed_files",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("index_version_id", sa.String(36), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("language", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("imports_json", sa.JSON(), nullable=False),
        sa.Column("references_json", sa.JSON(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["index_version_id"], ["index_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("index_version_id", "path", name="uq_indexed_file_version_path"),
    )
    op.create_index("ix_indexed_files_version_language", "indexed_files", ["index_version_id", "language"])

    op.create_table(
        "indexed_symbols",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("indexed_file_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("qualified_name", sa.String(1024), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["indexed_file_id"], ["indexed_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_indexed_symbols_file_name", "indexed_symbols", ["indexed_file_id", "name"])

    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("index_version_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("label", sa.String(1024), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("symbol", sa.String(1024), nullable=True),
        sa.Column("language", sa.String(32), nullable=True),
        sa.ForeignKeyConstraint(["index_version_id"], ["index_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", "index_version_id"),
    )
    op.create_index("ix_graph_nodes_version_kind", "graph_nodes", ["index_version_id", "kind"])

    op.create_table(
        "graph_edges",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("index_version_id", sa.String(36), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("target", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("confirmed", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["index_version_id"], ["index_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", "index_version_id"),
    )
    op.create_index("ix_graph_edges_version_kind", "graph_edges", ["index_version_id", "kind"])

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("agent_run_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("node", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_run_id", "sequence", name="uq_agent_step_run_sequence"),
    )

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("agent_step_id", sa.String(36), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("permission", sa.String(64), nullable=False),
        sa.Column("arguments_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.ForeignKeyConstraint(["agent_step_id"], ["agent_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_calls_step_tool", "tool_calls", ["agent_step_id", "tool_name"])

    op.create_table(
        "memory_claims",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(2048), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("used_in_run", sa.String(36), nullable=True),
        sa.Column("invalidated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_claims_repository_status", "memory_claims", ["repository_id", "status"])

    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            "CREATE VIRTUAL TABLE indexed_content_fts USING fts5(index_version_id UNINDEXED, file_id UNINDEXED, path, content, tokenize='unicode61')"
        )
    else:
        op.create_table(
            "indexed_content_fts",
            sa.Column("index_version_id", sa.String(36), nullable=False),
            sa.Column("file_id", sa.String(36), nullable=False),
            sa.Column("path", sa.String(2048), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(["index_version_id"], ["index_versions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["file_id"], ["indexed_files.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("file_id"),
        )
        op.create_index(
            "ix_indexed_content_fulltext",
            "indexed_content_fts",
            ["path", "content"],
            mysql_prefix="FULLTEXT",
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS indexed_content_fts")
    op.drop_index("ix_memory_claims_repository_status", table_name="memory_claims")
    op.drop_table("memory_claims")
    op.drop_index("ix_tool_calls_step_tool", table_name="tool_calls")
    op.drop_table("tool_calls")
    op.drop_table("agent_steps")
    op.drop_index("ix_graph_edges_version_kind", table_name="graph_edges")
    op.drop_table("graph_edges")
    op.drop_index("ix_graph_nodes_version_kind", table_name="graph_nodes")
    op.drop_table("graph_nodes")
    op.drop_index("ix_indexed_symbols_file_name", table_name="indexed_symbols")
    op.drop_table("indexed_symbols")
    op.drop_index("ix_indexed_files_version_language", table_name="indexed_files")
    op.drop_table("indexed_files")
    op.drop_index("ix_index_versions_repository_created", table_name="index_versions")
    op.drop_table("index_versions")
    op.drop_index("ix_pr_snapshots_pr_captured", table_name="pull_request_snapshots")
    op.drop_table("pull_request_snapshots")
    op.drop_index("ix_repository_syncs_repository_started", table_name="repository_syncs")
    op.drop_table("repository_syncs")
    op.drop_column("pull_requests", "analysis_status")
    op.drop_column("pull_requests", "changed_files")
    op.drop_column("pull_requests", "deletions")
    op.drop_column("pull_requests", "additions")
    op.drop_column("pull_requests", "draft")
    op.drop_column("repositories", "github_rate_remaining")
    op.drop_column("repositories", "last_synced_at")
    op.drop_column("repositories", "sync_etag")
    op.drop_column("repositories", "current_index_version")
    op.drop_column("repositories", "current_commit_sha")
    op.drop_column("findings", "model_profile")
    op.drop_column("findings", "verifier_status")
    op.drop_column("findings", "suggested_action")
    op.drop_column("findings", "symbol")
    op.drop_column("findings", "commit_sha")
    op.drop_column("findings", "category")
    op.drop_column("findings", "confidence")
    op.drop_column("agent_runs", "cancellation_requested")
    op.drop_column("agent_runs", "retry_count")
    op.drop_column("agent_runs", "latency_ms")
    op.drop_column("agent_runs", "output_tokens")
    op.drop_column("agent_runs", "input_tokens")
    op.drop_column("agent_runs", "model_profile")
    op.drop_column("agent_runs", "workflow_version")
