"""Add Pass 4a content columns: duplicate_reason, clustering_method, cluster_metadata_json

Revision ID: 0014_content_columns_pass4a
Revises: 0013_feed_reliability_tracking
Create Date: 2026-04-13 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0014_content_columns_pass4a"
down_revision: Union[str, None] = "0013_feed_reliability_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # --- content_items ---
    ci_columns = [c["name"] for c in sa.inspect(bind).get_columns("content_items")]
    if "duplicate_reason" not in ci_columns:
        op.add_column(
            "content_items",
            sa.Column("duplicate_reason", sa.Text(), nullable=True),
        )

    # --- content_clusters ---
    cc_columns = [c["name"] for c in sa.inspect(bind).get_columns("content_clusters")]
    if "clustering_method" not in cc_columns:
        op.add_column(
            "content_clusters",
            sa.Column("clustering_method", sa.String(50), nullable=True),
        )
    if "cluster_metadata_json" not in cc_columns:
        op.add_column(
            "content_clusters",
            sa.Column("cluster_metadata_json", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("content_clusters", "cluster_metadata_json")
    op.drop_column("content_clusters", "clustering_method")
    op.drop_column("content_items", "duplicate_reason")
