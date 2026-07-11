"""Persist parser exports and relationship provenance.

Revision ID: 20260711_0005
Revises: 20260710_0004
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260711_0005"
down_revision = "20260710_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_array_default = (
        sa.text("(JSON_ARRAY())")
        if op.get_bind().dialect.name == "mysql"
        else sa.text("'[]'")
    )
    op.add_column(
        "indexed_files",
        sa.Column("exports_json", sa.JSON(), nullable=False, server_default=json_array_default),
    )
    op.add_column(
        "indexed_files",
        sa.Column(
            "relationships_json",
            sa.JSON(),
            nullable=False,
            server_default=json_array_default,
        )
    )


def downgrade() -> None:
    op.drop_column("indexed_files", "relationships_json")
    op.drop_column("indexed_files", "exports_json")
