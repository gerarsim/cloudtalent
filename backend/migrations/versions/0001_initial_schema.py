"""Schéma initial : référentiel de compétences + relations normalisées

Revision ID: 0001
Revises:
Create Date: 2026-10-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default=""),
    )
    op.create_index("ix_skills_slug", "skills", ["slug"], unique=True)

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sector", sa.String(100), nullable=False, server_default=""),
        sa.Column("city", sa.String(100), nullable=False, server_default="Luxembourg"),
        sa.Column("contact_name", sa.String(150), nullable=False, server_default=""),
        sa.Column("email", sa.String(200), nullable=True),
    )

    op.create_table(
        "consultants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("email", sa.String(200), nullable=True, unique=True),
        sa.Column("experience_years", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tjm", sa.Float(), nullable=False, server_default="0"),
        sa.Column("available_from", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="Freelance"),
        sa.CheckConstraint("tjm >= 0", name="ck_consultant_tjm"),
        sa.CheckConstraint("experience_years >= 0", name="ck_consultant_exp"),
    )

    op.create_table(
        "missions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location", sa.String(100), nullable=False, server_default="Luxembourg"),
        sa.Column("duration_months", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("tjm_max", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="Ouverte"),
        sa.CheckConstraint("tjm_max >= 0", name="ck_mission_tjm"),
        sa.CheckConstraint("duration_months IS NULL OR duration_months > 0", name="ck_mission_duration"),
    )
    op.create_index("ix_missions_company_id", "missions", ["company_id"])

    op.create_table(
        "consultant_skills",
        sa.Column("consultant_id", sa.Integer(), sa.ForeignKey("consultants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="3"),
        sa.CheckConstraint("level BETWEEN 1 AND 5", name="ck_consultant_skill_level"),
    )
    op.create_index("ix_consultant_skills_skill_id", "consultant_skills", ["skill_id"])

    op.create_table(
        "mission_skills",
        sa.Column("mission_id", sa.Integer(), sa.ForeignKey("missions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("min_level", sa.Integer(), nullable=False, server_default="3"),
        sa.CheckConstraint("min_level BETWEEN 1 AND 5", name="ck_mission_skill_level"),
    )

    op.create_table(
        "trainings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="SET NULL"), nullable=True),
        sa.Column("level", sa.String(30), nullable=False, server_default="Débutant"),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("online", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("price >= 0", name="ck_training_price"),
    )


def downgrade() -> None:
    op.drop_table("trainings")
    op.drop_table("mission_skills")
    op.drop_index("ix_consultant_skills_skill_id", table_name="consultant_skills")
    op.drop_table("consultant_skills")
    op.drop_index("ix_missions_company_id", table_name="missions")
    op.drop_table("missions")
    op.drop_table("consultants")
    op.drop_table("companies")
    op.drop_index("ix_skills_slug", table_name="skills")
    op.drop_table("skills")
