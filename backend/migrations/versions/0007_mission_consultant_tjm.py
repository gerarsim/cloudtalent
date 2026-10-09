"""Mission : TJM proposé au consultant

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-09
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("missions") as batch:
        batch.add_column(sa.Column("consultant_tjm", sa.Float(), nullable=True))
        batch.create_check_constraint("ck_mission_consultant_tjm", "consultant_tjm IS NULL OR consultant_tjm >= 0")


def downgrade() -> None:
    with op.batch_alter_table("missions") as batch:
        batch.drop_constraint("ck_mission_consultant_tjm", type_="check")
        batch.drop_column("consultant_tjm")
