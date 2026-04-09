"""Add item_count column to content_clusters and FK on content_items.cluster_id

Revision ID: 0006_content_cluster_item_count
Revises: 0005_preferences
Create Date: 2026-04-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_content_cluster_item_count"
down_revision: Union[str, None] = "0005_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add item_count column to content_clusters
    op.add_column(
        "content_clusters",
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add foreign key constraint on content_items.cluster_id → content_clusters.id
    op.create_foreign_key(
        "fk_content_items_cluster_id",
        "content_items",
        "content_clusters",
        ["cluster_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_content_items_cluster_id", "content_items", type_="foreignkey"
    )
    op.drop_column("content_clusters", "item_count")
