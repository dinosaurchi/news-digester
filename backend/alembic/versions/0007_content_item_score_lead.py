"""Add score_breakdown_json and is_lead columns to content_items

Revision ID: 0007_content_item_score_lead
Revises: 0006_content_cluster_item_count
Create Date: 2026-04-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_content_item_score_lead"
down_revision: Union[str, None] = "0006_content_cluster_item_count"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "content_items",
        sa.Column("score_breakdown_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "content_items",
        sa.Column(
            "is_lead",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("content_items", "is_lead")
    op.drop_column("content_items", "score_breakdown_json")
