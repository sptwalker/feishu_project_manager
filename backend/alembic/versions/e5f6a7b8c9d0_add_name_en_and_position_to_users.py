"""add name_en and position to users

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-31 11:00:00.000000

用户管理增强：英文姓名(name_en) 与 职位(position)。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add name_en and position columns to users table."""
    op.add_column('users', sa.Column('name_en', sa.String(length=100), nullable=True, comment='英文姓名'))
    op.add_column('users', sa.Column('position', sa.String(length=100), nullable=True, comment='职位'))


def downgrade() -> None:
    """Remove name_en and position columns from users table."""
    op.drop_column('users', 'position')
    op.drop_column('users', 'name_en')
