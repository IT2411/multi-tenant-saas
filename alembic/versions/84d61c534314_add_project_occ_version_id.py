"""add_project_occ_version_id

Revision ID: 84d61c534314
Revises: 745e36ac4031
Create Date: 2026-08-28 13:42:12.483111+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84d61c534314'
down_revision: Union[str, None] = '745e36ac4031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add server_default='1' so existing rows automatically receive version 1
    op.add_column(
        "projects",
        sa.Column("version_id", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("projects", "version_id")
