import os
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from .database import Base

# Marge par défaut entre le TJM max payé par l'entreprise et le TJM proposé au consultant
CONSULTANT_MARGIN_PCT = float(os.getenv("CONSULTANT_MARGIN_PCT", "15"))


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
        CheckConstraint("days_per_month BETWEEN 0 AND 31", name="ck_consultant_days_per_month"),
        CheckConstraint("billing_tjm IS NULL OR billing_tjm >= 0", name="ck_consultant_billing_tjm"),
        CheckConstraint("tax_class IN ('1', '2')", name="ck_consultant_tax_class"),
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
    # Jours facturés par mois, base du calcul du salaire mensuel
    days_per_month: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    # Mission en cours, affectée par un admin
    mission_id: Mapped[int | None] = mapped_column(ForeignKey("missions.id", ondelete="SET NULL"), index=True)
    # TJM facturé au client pour ce consultant (admin uniquement) ; vide = TJM max de la mission
    billing_tjm: Mapped[float | None] = mapped_column(Float)
    # Classe d'impôt luxembourgeoise (1 = célibataire, 2 = marié / partenaire) pour la simulation de paie
    tax_class: Mapped[str] = mapped_column(String(2), default="1", server_default="1", nullable=False)

    skills: Mapped[list[ConsultantSkill]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ConsultantSkill.level.desc()"
    )
    mission: Mapped["Mission | None"] = relationship(lazy="selectin")
    cv: Mapped["ConsultantCV | None"] = relationship(cascade="all, delete-orphan", lazy="selectin")

    @property
    def effective_billing_tjm(self) -> float | None:
        """TJM facturé au client : celui fixé sur le consultant, sinon le TJM max de sa mission."""
        if self.billing_tjm is not None:
            return self.billing_tjm
        if self.mission is not None and self.mission.tjm_max:
            return self.mission.tjm_max
        return None


class ConsultantCV(Base):
    """CV du consultant (un seul, remplacé à chaque envoi). Le contenu n'est chargé qu'au téléchargement."""
    __tablename__ = "consultant_cvs"

    consultant_id: Mapped[int] = mapped_column(
        ForeignKey("consultants.id", ondelete="CASCADE"), primary_key=True
    )
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    data: Mapped[bytes] = deferred(mapped_column(LargeBinary, nullable=False))


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(100), default="Luxembourg", nullable=False)
    contact_name: Mapped[str] = mapped_column(String(150), default="", nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    website: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    address: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    vat_number: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Mission(Base):
    __tablename__ = "missions"
    __table_args__ = (
        CheckConstraint("tjm_max >= 0", name="ck_mission_tjm"),
        CheckConstraint("duration_months IS NULL OR duration_months > 0", name="ck_mission_duration"),
        CheckConstraint("consultant_tjm IS NULL OR consultant_tjm >= 0", name="ck_mission_consultant_tjm"),
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
    # Descriptif du poste (contexte, responsabilités…), saisi par l'admin ou l'entreprise
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # TJM proposé au consultant, fixé par l'admin ; jamais montré à l'entreprise
    consultant_tjm: Mapped[float | None] = mapped_column(Float)

    company: Mapped[Company | None] = relationship(lazy="joined")
    skills: Mapped[list[MissionSkill]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="MissionSkill.required.desc()"
    )

    @property
    def offered_tjm(self) -> float | None:
        """TJM proposé au consultant : celui fixé par l'admin, sinon TJM max − marge par défaut."""
        if self.consultant_tjm is not None:
            return self.consultant_tjm
        if self.tjm_max:
            return float(round(self.tjm_max * (1 - CONSULTANT_MARGIN_PCT / 100)))
        return None


# Chaque rôle est rattaché à exactement ce qu'il doit l'être (rien pour un admin)
USER_LINKS_CHECK = (
    "(role = 'admin' AND consultant_id IS NULL AND company_id IS NULL)"
    " OR (role = 'consultant' AND consultant_id IS NOT NULL AND company_id IS NULL)"
    " OR (role = 'company' AND company_id IS NOT NULL AND consultant_id IS NULL)"
)


class User(Base):
    """Compte de connexion. Un admin a tous les droits ; un consultant ne voit que sa fiche ;
    une entreprise partenaire gère sa fiche et ses missions."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'consultant', 'company')", name="ck_user_role"),
        CheckConstraint(USER_LINKS_CHECK, name="ck_user_links"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # Fiche consultant rattachée (uniquement pour le rôle consultant) ; supprimée avec elle
    consultant_id: Mapped[int | None] = mapped_column(
        ForeignKey("consultants.id", ondelete="CASCADE"), unique=True
    )
    # Entreprise rattachée (uniquement pour le rôle company) ; plusieurs comptes possibles
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
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


class Proposal(Base):
    """Consultant proposé par CloudTalent à une entreprise pour une de ses missions."""
    __tablename__ = "proposals"
    __table_args__ = (
        UniqueConstraint("mission_id", "consultant_id", name="uq_proposal_mission_consultant"),
        CheckConstraint("status IN ('Proposé', 'Retenu', 'Refusé')", name="ck_proposal_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True, nullable=False)
    consultant_id: Mapped[int] = mapped_column(
        ForeignKey("consultants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="Proposé", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mission: Mapped[Mission] = relationship(lazy="joined")
    consultant: Mapped[Consultant] = relationship(lazy="joined")


class Enrollment(Base):
    """Inscription d'un collaborateur d'une entreprise partenaire à une formation."""
    __tablename__ = "enrollments"
    __table_args__ = (
        CheckConstraint("status IN ('Demandée', 'Confirmée', 'Annulée')", name="ck_enrollment_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id", ondelete="CASCADE"), index=True, nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False)
    participant_name: Mapped[str] = mapped_column(String(150), nullable=False)
    participant_email: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Demandée", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    training: Mapped[Training] = relationship(lazy="joined")
    company: Mapped[Company] = relationship(lazy="joined")


class Invoice(Base):
    """Facture (ou relevé d'activité) mensuelle déposée par le consultant, signée par lui et son client.

    Les TJM sont figés au dépôt : un changement de tarif ultérieur ne modifie pas une facture existante."""
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("consultant_id", "period", name="uq_invoice_consultant_period"),
        CheckConstraint("status IN ('Déposée', 'Paiement demandé', 'Payée')", name="ck_invoice_status"),
        CheckConstraint("days > 0 AND days <= 31", name="ck_invoice_days"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    consultant_id: Mapped[int] = mapped_column(
        ForeignKey("consultants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    mission_id: Mapped[int | None] = mapped_column(ForeignKey("missions.id", ondelete="SET NULL"), index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # "AAAA-MM"
    days: Mapped[float] = mapped_column(Float, nullable=False)
    consultant_tjm: Mapped[float] = mapped_column(Float, nullable=False)
    billing_tjm: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="Déposée", nullable=False)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = deferred(mapped_column(LargeBinary, nullable=False))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    consultant: Mapped[Consultant] = relationship(lazy="joined")
    mission: Mapped[Mission | None] = relationship(lazy="joined")

    @property
    def amount(self) -> float | None:
        """Montant à facturer au client."""
        return None if self.billing_tjm is None else round(self.days * self.billing_tjm, 2)

    @property
    def consultant_amount(self) -> float:
        return round(self.days * self.consultant_tjm, 2)

    @property
    def margin(self) -> float | None:
        return None if self.amount is None else round(self.amount - self.consultant_amount, 2)


class Payslip(Base):
    """Fiche de paie mensuelle d'un consultant, établie par l'admin.

    Le calcul (brut → net luxembourgeois, voir app/payroll.py) est figé à la création ; l'admin
    peut joindre la fiche officielle de la fiduciaire."""
    __tablename__ = "payslips"
    __table_args__ = (
        UniqueConstraint("consultant_id", "period", name="uq_payslip_consultant_period"),
        CheckConstraint("gross >= 0", name="ck_payslip_gross"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    consultant_id: Mapped[int] = mapped_column(
        ForeignKey("consultants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # "AAAA-MM"
    tax_class: Mapped[str] = mapped_column(String(2), nullable=False)
    gross: Mapped[float] = mapped_column(Float, nullable=False)
    net: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    filename: Mapped[str | None] = mapped_column(String(200))
    content_type: Mapped[str | None] = mapped_column(String(100))
    size: Mapped[int | None] = mapped_column(Integer)
    data: Mapped[bytes | None] = deferred(mapped_column(LargeBinary))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    consultant: Mapped[Consultant] = relationship(lazy="joined")


__all__ = [
    "Skill",
    "ConsultantSkill",
    "MissionSkill",
    "Consultant",
    "Company",
    "Mission",
    "Training",
    "User",
    "Proposal",
    "Enrollment",
    "Invoice",
    "Payslip",
]
