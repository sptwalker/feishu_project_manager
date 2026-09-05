"""add ceo_focus (CEO重点关注/置顶)

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-09-05 10:00:00.000000

CEO重点关注：projects 增 ceo_focus（布尔，置顶标记，全局最多3个，仅管理员可设）。
存量行走 server_default='0' → 全部不钉，无需回填。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('ceo_focus', sa.Boolean(), nullable=False,
                                        server_default='0',
                                        comment='CEO重点关注（置顶），全局最多3个，仅管理员可设'))


def downgrade() -> None:
    op.drop_column('projects', 'ceo_focus')
