"""Add metadata_json column to reports

Revision ID: 0008_reports_metadata_json
Revises: 0007_content_item_score_lead
Create Date: 2026-04-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_reports_metadata_json"
down_revision: Union[str, None] = "0007_content_item_score_lead"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("reports")}
    if "metadata_json" in columns:
        return

    op.add_column(
        "reports",
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reports", "metadata_json")
