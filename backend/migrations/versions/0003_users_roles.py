"""Comptes utilisateurs : rôles admin / consultant

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(200), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column(
            "consultant_id", sa.Integer(),
            sa.ForeignKey("consultants.id", ondelete="CASCADE"), nullable=True, unique=True,
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("role IN ('admin', 'consultant')", name="ck_user_role"),
        sa.CheckConstraint(
            "(role = 'admin' AND consultant_id IS NULL) OR (role = 'consultant' AND consultant_id IS NOT NULL)",
            name="ck_user_consultant",
        ),
    )


def downgrade() -> None:
    op.drop_table("users")
