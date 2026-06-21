"""add status to users

Revision ID: b1c2d3e4f5a6
Revises: a3b4c5d6e7f8
Create Date: 2026-06-15 09:00:00.000000

用户准入审批：新增 status 列（pending/active/disabled）。
server_default='active' 让存量用户自动放行，无需数据回填。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status column to users（存量用户默认 active）。"""
    op.add_column(
        'users',
        sa.Column('status', sa.String(length=20), server_default='active',
                  nullable=False, comment='准入状态 pending待审/active启用/disabled禁用'),
    )
    op.create_index(op.f('ix_users_status'), 'users', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_status'), table_name='users')
    op.drop_column('users', 'status')
