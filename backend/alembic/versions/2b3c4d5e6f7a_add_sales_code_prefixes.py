"""add sales_code_prefixes table and prefix column

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-07-07 10:00:00.000000

前缀库 + sales_codes.prefix 列。销售码改为「前缀-随机」格式；旧测试码无对应前缀，
按需求清空既有 sales_codes 数据后再启用（用户已确认测试数据可清除）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2b3c4d5e6f7a'
down_revision: Union[str, Sequence[str], None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 清空旧格式测试码（无对应前缀，格式与新规则不符）
    op.execute("DELETE FROM sales_codes")

    op.add_column('sales_codes', sa.Column('prefix', sa.String(length=8), nullable=False,
                                           server_default='', comment='前缀（用于按前缀查询/限额统计）'))
    op.create_index(op.f('ix_sales_codes_prefix'), 'sales_codes', ['prefix'], unique=False)

    op.create_table(
        'sales_code_prefixes',
        sa.Column('prefix', sa.String(length=8), nullable=False, comment='前缀（大写字母数字，≤8位）'),
        sa.Column('remark', sa.String(length=200), nullable=False, server_default='', comment='备注'),
        sa.Column('max_count', sa.Integer(), nullable=True, comment='数量上限（空=无限制）'),
        sa.Column('disabled', sa.Boolean(), nullable=False, server_default=sa.text('0'), comment='是否禁用'),
        sa.Column('created_by', sa.String(length=100), nullable=False, server_default='', comment='添加者姓名快照'),
        sa.Column('created_by_id', sa.Integer(), nullable=True, comment='添加者用户ID（审计，可空）'),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sales_code_prefixes_id'), 'sales_code_prefixes', ['id'], unique=False)
    op.create_index(op.f('ix_sales_code_prefixes_prefix'), 'sales_code_prefixes', ['prefix'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_sales_code_prefixes_prefix'), table_name='sales_code_prefixes')
    op.drop_index(op.f('ix_sales_code_prefixes_id'), table_name='sales_code_prefixes')
    op.drop_table('sales_code_prefixes')
    op.drop_index(op.f('ix_sales_codes_prefix'), table_name='sales_codes')
    op.drop_column('sales_codes', 'prefix')
