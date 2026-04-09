"""Initial migration: workspaces, workspace_profiles, workspace_settings

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── workspaces table ─────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("customer", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    # ── workspace_profiles table ─────────────────────────────────────
    op.create_table(
        "workspace_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("business_name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("products", sa.JSON(), nullable=True),
        sa.Column("competitors", sa.JSON(), nullable=True),
        sa.Column("priority_themes", sa.JSON(), nullable=True),
        sa.Column("excluded_topics", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── workspace_settings table ─────────────────────────────────────
    op.create_table(
        "workspace_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("schedule", sa.JSON(), nullable=True),
        sa.Column(
            "report_style", sa.String(20), nullable=False, server_default="detailed"
        ),
        sa.Column("thresholds", sa.JSON(), nullable=True),
        sa.Column("retention", sa.JSON(), nullable=True),
        sa.Column("email_delivery", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("workspace_settings")
    op.drop_table("workspace_profiles")
    op.drop_table("workspaces")
