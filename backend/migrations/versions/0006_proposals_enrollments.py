"""Propositions de consultants aux entreprises, inscriptions aux formations

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-08
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mission_id", sa.Integer(), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consultant_id", sa.Integer(), sa.ForeignKey("consultants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="Proposé"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("mission_id", "consultant_id", name="uq_proposal_mission_consultant"),
        sa.CheckConstraint("status IN ('Proposé', 'Retenu', 'Refusé')", name="ck_proposal_status"),
    )
    op.create_index("ix_proposals_mission_id", "proposals", ["mission_id"])
    op.create_index("ix_proposals_consultant_id", "proposals", ["consultant_id"])
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("training_id", sa.Integer(), sa.ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("participant_name", sa.String(150), nullable=False),
        sa.Column("participant_email", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="Demandée"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('Demandée', 'Confirmée', 'Annulée')", name="ck_enrollment_status"),
    )
    op.create_index("ix_enrollments_training_id", "enrollments", ["training_id"])
    op.create_index("ix_enrollments_company_id", "enrollments", ["company_id"])


def downgrade() -> None:
    op.drop_table("enrollments")
    op.drop_table("proposals")
