"""Content items, content clusters, processing runs, and run events tables

Revision ID: 0004_content_and_runs
Revises: 0003_reports_and_feedback
Create Date: 2026-04-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_content_and_runs"
down_revision: Union[str, None] = "0003_reports_and_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── content_clusters table ────────────────────────────────────────
    op.create_table(
        "content_clusters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    # ── content_items table ───────────────────────────────────────────
    op.create_table(
        "content_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "feed_source_id",
            sa.String(36),
            sa.ForeignKey("feed_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("content_type", sa.String(30), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("summary_snippet", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("extracted_metadata_json", sa.JSON(), nullable=True),
        sa.Column("local_relevance_score", sa.Float(), nullable=True),
        sa.Column("llm_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("cluster_id", sa.String(36), nullable=True),
        sa.Column("inclusion_reason", sa.Text(), nullable=True),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column("report_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    # ── processing_runs table ─────────────────────────────────────────
    op.create_table(
        "processing_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column(
            "started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("affected_counts_json", sa.JSON(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    # ── processing_run_events table ───────────────────────────────────
    op.create_table(
        "processing_run_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("processing_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("processing_run_events")
    op.drop_table("processing_runs")
    op.drop_table("content_items")
    op.drop_table("content_clusters")
