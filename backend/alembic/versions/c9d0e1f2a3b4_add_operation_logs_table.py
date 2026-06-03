"""add operation_logs table

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-03 16:00:00.000000

系统操作日志表：记录用户登录与项目操作（仅向前记录），供管理员按时间范围查询。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'operation_logs',
        sa.Column('user_id', sa.Integer(), nullable=True, comment='操作人用户ID（可空）'),
        sa.Column('user_name', sa.String(length=100), nullable=False, comment='操作人姓名快照'),
        sa.Column('action', sa.String(length=30), nullable=False, comment='动作类型'),
        sa.Column('target', sa.String(length=200), nullable=True, comment='操作对象（如项目名）'),
        sa.Column('description', sa.Text(), nullable=False, comment='预渲染操作描述（不含人名）'),
        sa.Column('occurred_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='发生时间'),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_operation_logs_id'), 'operation_logs', ['id'], unique=False)
    op.create_index(op.f('ix_operation_logs_user_id'), 'operation_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_operation_logs_occurred_at'), 'operation_logs', ['occurred_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_operation_logs_occurred_at'), table_name='operation_logs')
    op.drop_index(op.f('ix_operation_logs_user_id'), table_name='operation_logs')
    op.drop_index(op.f('ix_operation_logs_id'), table_name='operation_logs')
    op.drop_table('operation_logs')
