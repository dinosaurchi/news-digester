"""Add publisher_name and publisher_domain columns to content_items.

Revision ID: 0015_publisher_info_columns
Revises: 0014_content_columns_pass4a
Create Date: 2026-04-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0015_publisher_info_columns"
down_revision: Union[str, None] = "0014_content_columns_pass4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    ci_columns = [c["name"] for c in sa.inspect(bind).get_columns("content_items")]
    if "publisher_name" not in ci_columns:
        op.add_column(
            "content_items",
            sa.Column("publisher_name", sa.String(255), nullable=True),
        )
    if "publisher_domain" not in ci_columns:
        op.add_column(
            "content_items",
            sa.Column("publisher_domain", sa.String(255), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("content_items", "publisher_domain")
    op.drop_column("content_items", "publisher_name")
