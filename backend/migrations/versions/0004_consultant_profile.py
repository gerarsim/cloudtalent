"""Espace consultant : mission en cours, jours facturés par mois, CV

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-08
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("consultants") as batch:
        batch.add_column(sa.Column("days_per_month", sa.Integer(), nullable=False, server_default="20"))
        batch.add_column(sa.Column("mission_id", sa.Integer(), nullable=True))
        batch.create_check_constraint("ck_consultant_days_per_month", "days_per_month BETWEEN 0 AND 31")
        batch.create_foreign_key(
            "fk_consultants_mission_id", "missions", ["mission_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_index("ix_consultants_mission_id", ["mission_id"])
    op.create_table(
        "consultant_cvs",
        sa.Column(
            "consultant_id", sa.Integer(),
            sa.ForeignKey("consultants.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("consultant_cvs")
    with op.batch_alter_table("consultants") as batch:
        batch.drop_index("ix_consultants_mission_id")
        batch.drop_constraint("fk_consultants_mission_id", type_="foreignkey")
        batch.drop_constraint("ck_consultant_days_per_month", type_="check")
        batch.drop_column("mission_id")
        batch.drop_column("days_per_month")
