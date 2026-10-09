"""Classe d'impôt des consultants, fiches de paie

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-09
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("consultants") as batch:
        batch.add_column(sa.Column("tax_class", sa.String(2), nullable=False, server_default="1"))
        batch.create_check_constraint("ck_consultant_tax_class", "tax_class IN ('1', '2')")
    op.create_table(
        "payslips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("consultant_id", sa.Integer(), sa.ForeignKey("consultants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("tax_class", sa.String(2), nullable=False),
        sa.Column("gross", sa.Float(), nullable=False),
        sa.Column("net", sa.Float(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("filename", sa.String(200), nullable=True),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("data", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("consultant_id", "period", name="uq_payslip_consultant_period"),
        sa.CheckConstraint("gross >= 0", name="ck_payslip_gross"),
    )
    op.create_index("ix_payslips_consultant_id", "payslips", ["consultant_id"])


def downgrade() -> None:
    op.drop_table("payslips")
    with op.batch_alter_table("consultants") as batch:
        batch.drop_constraint("ck_consultant_tax_class", type_="check")
        batch.drop_column("tax_class")
