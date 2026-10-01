from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Skill(Base):
    """Référentiel de compétences. `slug` est la forme normalisée (unique)."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50), default="", nullable=False)


class ConsultantSkill(Base):
    __tablename__ = "consultant_skills"
    __table_args__ = (CheckConstraint("level BETWEEN 1 AND 5", name="ck_consultant_skill_level"),)

    consultant_id: Mapped[int] = mapped_column(
        ForeignKey("consultants.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    level: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    skill: Mapped[Skill] = relationship(lazy="joined")


class MissionSkill(Base):
    __tablename__ = "mission_skills"
    __table_args__ = (CheckConstraint("min_level BETWEEN 1 AND 5", name="ck_mission_skill_level"),)

    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_level: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    skill: Mapped[Skill] = relationship(lazy="joined")


class Consultant(Base):
    __tablename__ = "consultants"
    __table_args__ = (
        CheckConstraint("tjm >= 0", name="ck_consultant_tjm"),
        CheckConstraint("experience_years >= 0", name="ck_consultant_exp"),
        CheckConstraint("reserve_pct BETWEEN 0 AND 100", name="ck_consultant_reserve_pct"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), unique=True)
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tjm: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    # Part du TJM que le consultant met de côté en réserve (0-100 %)
    reserve_pct: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    available_from: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="Freelance", nullable=False)

    skills: Mapped[list[ConsultantSkill]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ConsultantSkill.level.desc()"
    )


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(100), default="Luxembourg", nullable=False)
    contact_name: Mapped[str] = mapped_column(String(150), default="", nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))


class Mission(Base):
    __tablename__ = "missions"
    __table_args__ = (
        CheckConstraint("tjm_max >= 0", name="ck_mission_tjm"),
        CheckConstraint("duration_months IS NULL OR duration_months > 0", name="ck_mission_duration"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    location: Mapped[str] = mapped_column(String(100), default="Luxembourg", nullable=False)
    duration_months: Mapped[int | None] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date)
    tjm_max: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="Ouverte", nullable=False)

    company: Mapped[Company | None] = relationship(lazy="joined")
    skills: Mapped[list[MissionSkill]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="MissionSkill.required.desc()"
    )


class User(Base):
    """Compte de connexion. Un admin a tous les droits ; un consultant ne voit que sa fiche."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'consultant')", name="ck_user_role"),
        CheckConstraint(
            "(role = 'admin' AND consultant_id IS NULL) OR (role = 'consultant' AND consultant_id IS NOT NULL)",
            name="ck_user_consultant",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # Fiche consultant rattachée (uniquement pour le rôle consultant) ; supprimée avec elle
    consultant_id: Mapped[int | None] = mapped_column(
        ForeignKey("consultants.id", ondelete="CASCADE"), unique=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    consultant: Mapped[Consultant | None] = relationship(lazy="joined")


class Training(Base):
    __tablename__ = "trainings"
    __table_args__ = (CheckConstraint("price >= 0", name="ck_training_price"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"))
    level: Mapped[str] = mapped_column(String(30), default="Débutant", nullable=False)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    online: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    skill: Mapped[Skill | None] = relationship(lazy="joined")


__all__ = [
    "Skill",
    "ConsultantSkill",
    "MissionSkill",
    "Consultant",
    "Company",
    "Mission",
    "Training",
    "User",
]
