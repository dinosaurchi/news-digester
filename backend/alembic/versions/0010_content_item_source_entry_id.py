"""Add source_entry_id to content_items

Revision ID: 0010_content_item_source_entry_id
Revises: 0009_users
Create Date: 2026-04-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0010_content_item_source_entry_id"
down_revision: Union[str, None] = "0009_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in sa.inspect(bind).get_columns("content_items")]
    if "source_entry_id" in columns:
        return

    op.add_column(
        "content_items",
        sa.Column("source_entry_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_items", "source_entry_id")
