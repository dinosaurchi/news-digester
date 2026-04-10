"""Widen source_entry_id column from String(255) to String(2048)

Revision ID: 0012_widen_source_entry_id
Revises: 0011_feed_source_last_error_at
Create Date: 2026-04-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0012_widen_source_entry_id"
down_revision: Union[str, None] = "0011_feed_source_last_error_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("content_items") as batch_op:
        batch_op.alter_column(
            "source_entry_id",
            existing_type=sa.String(255),
            type_=sa.String(2048),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("content_items") as batch_op:
        batch_op.alter_column(
            "source_entry_id",
            existing_type=sa.String(2048),
            type_=sa.String(255),
            existing_nullable=True,
        )
