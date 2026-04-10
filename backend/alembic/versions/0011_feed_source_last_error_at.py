"""Add last_error_at to feed_sources

Revision ID: 0011_feed_source_last_error_at
Revises: 0010_content_item_source_entry_id
Create Date: 2026-04-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0011_feed_source_last_error_at"
down_revision: Union[str, None] = "0010_content_item_source_entry_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in sa.inspect(bind).get_columns("feed_sources")]
    if "last_error_at" in columns:
        return

    op.add_column(
        "feed_sources",
        sa.Column("last_error_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("feed_sources", "last_error_at")
