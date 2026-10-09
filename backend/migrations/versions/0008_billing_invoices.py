"""TJM facturé au client par consultant, factures mensuelles signées

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-09
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("consultants") as batch:
        batch.add_column(sa.Column("billing_tjm", sa.Float(), nullable=True))
        batch.create_check_constraint("ck_consultant_billing_tjm", "billing_tjm IS NULL OR billing_tjm >= 0")
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("consultant_id", sa.Integer(), sa.ForeignKey("consultants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mission_id", sa.Integer(), sa.ForeignKey("missions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("days", sa.Float(), nullable=False),
        sa.Column("consultant_tjm", sa.Float(), nullable=False),
        sa.Column("billing_tjm", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Déposée"),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("consultant_id", "period", name="uq_invoice_consultant_period"),
        sa.CheckConstraint("status IN ('Déposée', 'Paiement demandé', 'Payée')", name="ck_invoice_status"),
        sa.CheckConstraint("days > 0 AND days <= 31", name="ck_invoice_days"),
    )
    op.create_index("ix_invoices_consultant_id", "invoices", ["consultant_id"])
    op.create_index("ix_invoices_mission_id", "invoices", ["mission_id"])


def downgrade() -> None:
    op.drop_table("invoices")
    with op.batch_alter_table("consultants") as batch:
        batch.drop_constraint("ck_consultant_billing_tjm", type_="check")
        batch.drop_column("billing_tjm")
