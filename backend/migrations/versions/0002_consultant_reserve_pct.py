"""Consultant : pourcentage du TJM mis en réserve

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # batch_alter_table : SQLite (tests) ne sait pas ajouter une contrainte CHECK via ALTER
    with op.batch_alter_table("consultants") as batch:
        batch.add_column(sa.Column("reserve_pct", sa.Float(), nullable=False, server_default="0"))
        batch.create_check_constraint("ck_consultant_reserve_pct", "reserve_pct BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("consultants") as batch:
        batch.drop_constraint("ck_consultant_reserve_pct", type_="check")
        batch.drop_column("reserve_pct")
