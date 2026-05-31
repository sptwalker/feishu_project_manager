"""add short_name to departments

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add short_name column to departments table."""
    op.add_column('departments', sa.Column('short_name', sa.String(length=50), nullable=True, comment='部门简称'))


def downgrade() -> None:
    """Remove short_name column from departments table."""
    op.drop_column('departments', 'short_name')
