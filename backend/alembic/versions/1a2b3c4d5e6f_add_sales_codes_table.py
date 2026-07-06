"""add sales_codes table

Revision ID: 1a2b3c4d5e6f
Revises: b1c2d3e4f5a6
Create Date: 2026-07-06 20:00:00.000000

内部销售码表：管理员批量生成的随机销售码，逐条/批量核销。created_at 即生成时间。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sales_codes',
        sa.Column('code', sa.String(length=32), nullable=False, comment='销售码（随机，唯一）'),
        sa.Column('generated_by', sa.String(length=100), nullable=False, comment='生成人姓名快照'),
        sa.Column('generated_by_id', sa.Integer(), nullable=True, comment='生成人用户ID（审计，可空）'),
        sa.Column('issued_to', sa.String(length=200), nullable=False, comment='发放对象'),
        sa.Column('redeemed', sa.Boolean(), nullable=False, comment='是否已核销'),
        sa.Column('redeemed_at', sa.DateTime(), nullable=True, comment='核销时间'),
        sa.Column('redeemed_by', sa.String(length=100), nullable=True, comment='核销人姓名快照'),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sales_codes_id'), 'sales_codes', ['id'], unique=False)
    op.create_index(op.f('ix_sales_codes_code'), 'sales_codes', ['code'], unique=True)
    op.create_index(op.f('ix_sales_codes_redeemed'), 'sales_codes', ['redeemed'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sales_codes_redeemed'), table_name='sales_codes')
    op.drop_index(op.f('ix_sales_codes_code'), table_name='sales_codes')
    op.drop_index(op.f('ix_sales_codes_id'), table_name='sales_codes')
    op.drop_table('sales_codes')
