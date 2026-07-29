"""add discuss_perms to users

Revision ID: c4d5e6f7a8b9
Revises: 2b3c4d5e6f7a
Create Date: 2026-07-30 10:00:00.000000

留言区细粒度授权：新增 discuss_perms 列（CSV，键取自 reply/hide/delete/block/announce），
与系统角色脱钩。server_default='' 让存量用户默认无权；随后回填现有系统管理员为全部权限，
避免脱钩后当前管理员被锁在留言区管理之外。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = '2b3c4d5e6f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALL_PERMS = 'reply,hide,delete,block,announce'


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('discuss_perms', sa.String(length=200), server_default='',
                  nullable=False, comment='留言区权限CSV'),
    )
    # 现有系统管理员一次性获得全部留言区权限（保持连续，之后纯按勾选）
    op.execute(
        "UPDATE users SET discuss_perms = '%s' WHERE role = 'admin'" % _ALL_PERMS
    )


def downgrade() -> None:
    op.drop_column('users', 'discuss_perms')
