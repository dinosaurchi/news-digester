"""Add users table

Revision ID: 0009_users
Revises: 0008_reports_metadata_json
Create Date: 2026-04-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0009_users"
down_revision: Union[str, None] = "0008_reports_metadata_json"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "users" in tables:
        return

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="admin"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
