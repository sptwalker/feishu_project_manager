"""add project_id to operation_logs

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-06-05 12:00:00.000000

给操作日志表加 project_id（可空，带索引），用于「项目详情 › 历史修改记录」按项目查询。
不加外键/级联——项目删除时日志保留。旧日志 project_id 为 NULL。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite 加列+索引用 batch_alter_table（走重建流程）
    with op.batch_alter_table('operation_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('project_id', sa.Integer(), nullable=True,
                                      comment='关联项目ID（按项目查历史；不级联，项目删除后日志保留）'))
        batch_op.create_index(batch_op.f('ix_operation_logs_project_id'), ['project_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('operation_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_operation_logs_project_id'))
        batch_op.drop_column('project_id')
