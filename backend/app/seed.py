"""Données de démonstration, insérées seulement si la base est vide."""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import Company, Consultant, ConsultantSkill, Mission, MissionSkill, Training, User
from .skills import get_or_create_skill


def _cskills(db: Session, spec: dict[str, int]) -> list[ConsultantSkill]:
    return [ConsultantSkill(skill_id=get_or_create_skill(db, n).id, level=l) for n, l in spec.items()]


DEMO_EMAIL, DEMO_PASSWORD = "ahmed.benali@example.com", "consultant123"


def ensure_demo_account(db: Session) -> None:
    """Crée le compte consultant de démo s'il manque.

    Indépendant du seed : une base remplie avant l'arrivée des comptes (v0.2) a déjà
    ses consultants, le seed ne repasse donc pas et le compte n'existerait jamais.
    """
    ahmed = db.scalar(select(Consultant).where(Consultant.email == DEMO_EMAIL))
    if ahmed is None:
        return
    if db.scalar(select(User.id).where((User.email == DEMO_EMAIL) | (User.consultant_id == ahmed.id))):
        return
    db.add(User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD),
                role="consultant", consultant_id=ahmed.id))
    db.commit()


DEMO_COMPANY_NAME = "Demo Bank Luxembourg"
DEMO_COMPANY_EMAIL, DEMO_COMPANY_PASSWORD = "rh@demobank.example.com", "entreprise123"


def ensure_demo_company_account(db: Session) -> None:
    """Crée le compte entreprise partenaire de démo s'il manque (même logique que le consultant)."""
    bank = db.scalar(select(Company).where(Company.name == DEMO_COMPANY_NAME).limit(1))
    if bank is None or db.scalar(select(User.id).where(User.email == DEMO_COMPANY_EMAIL)):
        return
    db.add(User(email=DEMO_COMPANY_EMAIL, password_hash=hash_password(DEMO_COMPANY_PASSWORD),
                role="company", company_id=bank.id))
    db.commit()


def seed(db: Session) -> None:
    if db.scalar(select(func.count(Consultant.id))):
        ensure_demo_account(db)
        ensure_demo_company_account(db)
        return

    today = date.today()

    ahmed = Consultant(
        name="Ahmed Benali", title="Senior DevOps Engineer", email="ahmed.benali@example.com",
        experience_years=8, tjm=700, reserve_pct=10, status="Portage",
        skills=_cskills(db, {"AWS": 5, "EKS": 4, "Kubernetes": 4, "Terraform": 4, "Docker": 4,
                             "GitLab CI/CD": 4, "ArgoCD": 3, "Linux": 4}),
    )
    db.add_all([
        ahmed,
        Consultant(
            name="Sophie Martin", title="Cloud Engineer", email="sophie.martin@example.com",
            experience_years=6, tjm=650, status="Portage", available_from=today + timedelta(days=30),
            skills=_cskills(db, {"Azure": 5, "AKS": 4, "Terraform": 3, "Azure DevOps": 4, "Docker": 3,
                                 "PowerShell": 4}),
        ),
        Consultant(
            name="Marc Dupont", title="Platform Engineer", email="marc.dupont@example.com",
            experience_years=10, tjm=750, status="Freelance",
            skills=_cskills(db, {"AWS": 4, "Kubernetes": 5, "Terraform": 5, "Helm": 4, "ArgoCD": 4,
                                 "GitHub Actions": 3, "DevSecOps": 3}),
        ),
    ])

    bank = Company(name=DEMO_COMPANY_NAME, sector="Banking", city="Luxembourg",
                   contact_name="IT Procurement", email="demo@example.com", phone="+352 00 00 00",
                   address="1 boulevard Royal, L-2449",
                   description="Banque de démonstration, partenaire CloudTalent.")
    db.add(bank)
    db.flush()

    mission_skills = {"AWS": (True, 4), "EKS": (True, 3), "Kubernetes": (True, 4),
                      "Terraform": (True, 3), "GitLab CI/CD": (False, 3), "ArgoCD": (False, 3)}
    mission = Mission(
        title="Senior DevOps Engineer", company_id=bank.id, location="Luxembourg",
        duration_months=6, start_date=today + timedelta(days=14), tjm_max=800, status="Ouverte",
        skills=[MissionSkill(skill_id=get_or_create_skill(db, n).id, required=r, min_level=l)
                for n, (r, l) in mission_skills.items()],
    )
    db.add(mission)
    db.flush()
    ahmed.mission_id = mission.id  # mission en cours visible dans l'espace consultant

    db.add_all([
        Training(title="AWS & Kubernetes pour DevOps", skill_id=get_or_create_skill(db, "Kubernetes").id,
                 level="Avancé", duration_days=5, price=1500),
        Training(title="Terraform & Infrastructure as Code", skill_id=get_or_create_skill(db, "Terraform").id,
                 level="Intermédiaire", duration_days=3, price=900),
    ])
    db.commit()
    # Comptes de démonstration : le consultant ne voit que sa fiche, l'entreprise ses missions
    ensure_demo_account(db)
    ensure_demo_company_account(db)
