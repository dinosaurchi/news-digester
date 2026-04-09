"""Reports, report messages, and feedback events tables

Revision ID: 0003_reports_and_feedback
Revises: 0002_feed_sources
Create Date: 2026-04-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_reports_and_feedback"
down_revision: Union[str, None] = "0002_feed_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── reports table ────────────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=True),
        sa.Column("period_end", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("markdown_body", sa.Text(), nullable=True),
        sa.Column("run_id", sa.String(36), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    # ── report_messages table ────────────────────────────────────────
    op.create_table(
        "report_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "thread_id",
            sa.String(36),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("feedback", sa.String(10), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("parent_message_id", sa.String(36), nullable=True),
        sa.Column(
            "sent_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    # ── feedback_events table ────────────────────────────────────────
    op.create_table(
        "feedback_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("report_id", sa.String(36), nullable=True),
        sa.Column("thread_id", sa.String(36), nullable=True),
        sa.Column("message_id", sa.String(36), nullable=True),
        sa.Column("content_item_id", sa.String(36), nullable=True),
        sa.Column("feedback_type", sa.String(30), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("feedback_events")
    op.drop_table("report_messages")
    op.drop_table("reports")
