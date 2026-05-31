"""add related_name and progress_log to projects

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-31

项目详情页需要：相关人(related_name) 与 项目进展记录(progress_log, JSON)。
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("related_name", sa.String(length=200), nullable=True, comment="相关人"))
        batch.add_column(sa.Column("progress_log", sa.JSON(), nullable=True, comment="项目进展记录"))


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("progress_log")
        batch.drop_column("related_name")
