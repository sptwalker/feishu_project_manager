"""decouple owner from users: owner_id -> owner_name

Revision ID: a1b2c3d4e5f6
Revises: 3250137362e7
Create Date: 2026-05-30

将 projects / tasks / risks 的 owner_id(外键->users) 改为 owner_name(字符串)，
使项目数据与用户账号解耦：增删用户、改角色不影响项目数据。
SQLite 通过 batch 模式重建表。
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "3250137362e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # projects
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("owner_name", sa.String(length=100), nullable=True, comment="负责人姓名（与用户账号解耦）"))
        batch.drop_column("owner_id")
    # tasks
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("owner_name", sa.String(length=100), nullable=True, comment="负责人姓名（与用户账号解耦）"))
        batch.drop_column("owner_id")
    # risks
    with op.batch_alter_table("risks") as batch:
        batch.add_column(sa.Column("owner_name", sa.String(length=100), nullable=True, comment="负责人姓名（与用户账号解耦）"))
        batch.drop_column("owner_id")


def downgrade() -> None:
    with op.batch_alter_table("risks") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch.drop_column("owner_name")
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch.drop_column("owner_name")
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch.drop_column("owner_name")
