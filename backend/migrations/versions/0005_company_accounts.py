"""Entreprises partenaires : comptes rôle « company », fiche entreprise complète, descriptif de mission

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-08
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

LINKS = (
    "(role = 'admin' AND consultant_id IS NULL AND company_id IS NULL)"
    " OR (role = 'consultant' AND consultant_id IS NOT NULL AND company_id IS NULL)"
    " OR (role = 'company' AND company_id IS NOT NULL AND consultant_id IS NULL)"
)
COMPANY_COLUMNS = [("phone", 50), ("website", 200), ("address", 300), ("vat_number", 50)]


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch:
        for name, length in COMPANY_COLUMNS:
            batch.add_column(sa.Column(name, sa.String(length), nullable=False, server_default=""))
        batch.add_column(sa.Column("description", sa.Text(), nullable=False, server_default=""))
    with op.batch_alter_table("missions") as batch:
        batch.add_column(sa.Column("description", sa.Text(), nullable=False, server_default=""))
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("company_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_users_company_id", "companies", ["company_id"], ["id"], ondelete="CASCADE")
        batch.create_index("ix_users_company_id", ["company_id"])
        batch.drop_constraint("ck_user_consultant", type_="check")
        batch.drop_constraint("ck_user_role", type_="check")
        batch.create_check_constraint("ck_user_role", "role IN ('admin', 'consultant', 'company')")
        batch.create_check_constraint("ck_user_links", LINKS)


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE role = 'company'")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_user_links", type_="check")
        batch.drop_constraint("ck_user_role", type_="check")
        batch.create_check_constraint("ck_user_role", "role IN ('admin', 'consultant')")
        batch.create_check_constraint(
            "ck_user_consultant",
            "(role = 'admin' AND consultant_id IS NULL) OR (role = 'consultant' AND consultant_id IS NOT NULL)",
        )
        batch.drop_index("ix_users_company_id")
        batch.drop_constraint("fk_users_company_id", type_="foreignkey")
        batch.drop_column("company_id")
    with op.batch_alter_table("missions") as batch:
        batch.drop_column("description")
    with op.batch_alter_table("companies") as batch:
        batch.drop_column("description")
        for name, _ in reversed(COMPANY_COLUMNS):
            batch.drop_column(name)
