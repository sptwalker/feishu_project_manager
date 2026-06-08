"""add server-side timer + controller columns to meeting_records

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-06-08 10:00:00.000000

会议计时服务端化 + 主控机制：给 meeting_records 加
- timer_state(JSON)：计时锚点
- controller_client_id(String)：当前主控浏览器 id
- controller_heartbeat_at(DateTime)：主控心跳
- controller_version(Integer, default 0)：认领/接管 CAS 版本
均仅 active 行有效，归档时清空。存量行默认 NULL / version=0。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('meeting_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timer_state', sa.JSON(), nullable=True,
                                      comment='服务端计时锚点（主控控制，客户端本地推算）'))
        batch_op.add_column(sa.Column('controller_client_id', sa.String(length=64), nullable=True,
                                      comment='当前主控浏览器 client_id；null=无主控'))
        batch_op.add_column(sa.Column('controller_heartbeat_at', sa.DateTime(), nullable=True,
                                      comment='主控最后心跳时刻'))
        batch_op.add_column(sa.Column('controller_version', sa.Integer(), nullable=False,
                                      server_default='0', comment='主控认领/接管 CAS 版本'))


def downgrade() -> None:
    with op.batch_alter_table('meeting_records', schema=None) as batch_op:
        batch_op.drop_column('controller_version')
        batch_op.drop_column('controller_heartbeat_at')
        batch_op.drop_column('controller_client_id')
        batch_op.drop_column('timer_state')
