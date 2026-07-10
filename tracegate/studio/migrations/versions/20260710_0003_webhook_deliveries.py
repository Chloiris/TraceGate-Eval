"""Add deduplicated GitHub webhook delivery records.

Revision ID: 20260710_0003
Revises: 20260710_0002
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260710_0003"
down_revision: str | None = "20260710_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("delivery_id", sa.String(128), nullable=False),
        sa.Column("event", sa.String(128), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("repository_full_name", sa.String(201), nullable=True),
        sa.Column("pull_request_number", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("delivery_id", name="uq_webhook_deliveries_delivery_id"),
    )
    op.create_index("ix_webhook_deliveries_received", "webhook_deliveries", ["received_at"])


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_received", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
