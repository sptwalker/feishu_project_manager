"""add version (optimistic lock) to projects

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-07 14:00:00.000000

给项目表加 version 乐观锁版本号（非空，默认 1）。
配合应用层比对 + SQLAlchemy version_id_col 的 SQL 级 CAS，
防止多用户并发编辑同一项目时的"最后写入者赢"静默覆盖。
存量行由 server_default 自动回填为 1。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite 加列用 batch_alter_table（走重建流程）；server_default 保证存量行非空
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=False,
                                      server_default='1',
                                      comment='乐观锁版本号（每次更新自动+1）'))


def downgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('version')
