"""add meeting_records table

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-03 09:00:00.000000

周会记录归档表：持久化每次周例会的次数/日期/记录人/内容快照/飞书文档链接。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'meeting_records',
        sa.Column('session', sa.Integer(), nullable=False, comment='周会次数（唯一）'),
        sa.Column('meeting_date', sa.Date(), nullable=False, comment='会议日期'),
        sa.Column('recorder', sa.String(length=100), nullable=True, comment='记录人姓名'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='active=进行中 / archived=已结束'),
        sa.Column('content_snapshot', sa.JSON(), nullable=True, comment='结束时落库的各项目进展快照'),
        sa.Column('doc_url', sa.String(length=500), nullable=True, comment='飞书文档链接（发送后回填）'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='操作人用户ID（审计用，可空）'),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_meeting_records_id'), 'meeting_records', ['id'], unique=False)
    op.create_index(op.f('ix_meeting_records_session'), 'meeting_records', ['session'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_meeting_records_session'), table_name='meeting_records')
    op.drop_index(op.f('ix_meeting_records_id'), table_name='meeting_records')
    op.drop_table('meeting_records')
