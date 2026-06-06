"""add started_at/ended_at to meeting_records

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-06-06 10:00:00.000000

给周会记录表加 started_at/ended_at（均可空，DateTime），
记录汇报会议的实际开始/结束时刻。旧记录两列为 NULL。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite 加列用 batch_alter_table（走重建流程）
    with op.batch_alter_table('meeting_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('started_at', sa.DateTime(), nullable=True,
                                      comment='汇报会议开始时刻'))
        batch_op.add_column(sa.Column('ended_at', sa.DateTime(), nullable=True,
                                      comment='汇报会议结束时刻'))


def downgrade() -> None:
    with op.batch_alter_table('meeting_records', schema=None) as batch_op:
        batch_op.drop_column('ended_at')
        batch_op.drop_column('started_at')
