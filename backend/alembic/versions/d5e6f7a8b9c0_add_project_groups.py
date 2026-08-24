"""add project groups (parent_id, is_group)

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-24 10:00:00.000000

项目组层级：projects 增 parent_id（自引用，子项目指向组）+ is_group（组容器标记）。
存量行 is_group 走 server_default='0'、parent_id 为 NULL → 全部视为独立顶层项目，无需回填。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('parent_id', sa.Integer(), nullable=True,
                                        comment='所属项目组ID（子项目指向组；顶层为空）'))
    op.create_index('ix_projects_parent_id', 'projects', ['parent_id'])
    op.add_column('projects', sa.Column('is_group', sa.Boolean(), nullable=False,
                                        server_default='0', comment='是否为项目组容器'))


def downgrade() -> None:
    op.drop_column('projects', 'is_group')
    op.drop_index('ix_projects_parent_id', table_name='projects')
    op.drop_column('projects', 'parent_id')
