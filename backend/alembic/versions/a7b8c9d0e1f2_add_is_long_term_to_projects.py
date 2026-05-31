"""add is_long_term to projects

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-01 13:00:00.000000

长期项目标记：勾选后不显示完成度，显示“长期项目”。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('is_long_term', sa.Boolean(), nullable=False, server_default=sa.false(), comment='长期项目（不显示完成度）'))


def downgrade() -> None:
    op.drop_column('projects', 'is_long_term')
