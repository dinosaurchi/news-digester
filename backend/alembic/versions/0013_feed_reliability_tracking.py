"""Add feed reliability tracking columns to feed_sources

Revision ID: 0013_feed_reliability_tracking
Revises: 0012_widen_source_entry_id
Create Date: 2026-04-13 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0013_feed_reliability_tracking"
down_revision: Union[str, None] = "0012_widen_source_entry_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in sa.inspect(bind).get_columns("feed_sources")]

    if "last_successful_fetch_at" not in columns:
        op.add_column(
            "feed_sources",
            sa.Column("last_successful_fetch_at", sa.DateTime(), nullable=True),
        )
    if "consecutive_fetch_failures" not in columns:
        op.add_column(
            "feed_sources",
            sa.Column(
                "consecutive_fetch_failures",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if "total_fetch_count" not in columns:
        op.add_column(
            "feed_sources",
            sa.Column(
                "total_fetch_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    op.drop_column("feed_sources", "total_fetch_count")
    op.drop_column("feed_sources", "consecutive_fetch_failures")
    op.drop_column("feed_sources", "last_successful_fetch_at")
