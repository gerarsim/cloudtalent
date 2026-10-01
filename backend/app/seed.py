"""Données de démonstration, insérées seulement si la base est vide."""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Company, Consultant, ConsultantSkill, Mission, MissionSkill, Training
from .skills import get_or_create_skill


def _cskills(db: Session, spec: dict[str, int]) -> list[ConsultantSkill]:
    return [ConsultantSkill(skill_id=get_or_create_skill(db, n).id, level=l) for n, l in spec.items()]


def seed(db: Session) -> None:
    if db.scalar(select(func.count(Consultant.id))):
        return

    today = date.today()

    db.add_all([
        Consultant(
            name="Ahmed Benali", title="Senior DevOps Engineer", email="ahmed.benali@example.com",
            experience_years=8, tjm=700, status="Freelance",
            skills=_cskills(db, {"AWS": 5, "EKS": 4, "Kubernetes": 4, "Terraform": 4, "Docker": 4,
                                 "GitLab CI/CD": 4, "ArgoCD": 3, "Linux": 4}),
        ),
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

    bank = Company(name="Demo Bank Luxembourg", sector="Banking", city="Luxembourg",
                   contact_name="IT Procurement", email="demo@example.com")
    db.add(bank)
    db.flush()

    mission_skills = {"AWS": (True, 4), "EKS": (True, 3), "Kubernetes": (True, 4),
                      "Terraform": (True, 3), "GitLab CI/CD": (False, 3), "ArgoCD": (False, 3)}
    db.add(Mission(
        title="Senior DevOps Engineer", company_id=bank.id, location="Luxembourg",
        duration_months=6, start_date=today + timedelta(days=14), tjm_max=800, status="Ouverte",
        skills=[MissionSkill(skill_id=get_or_create_skill(db, n).id, required=r, min_level=l)
                for n, (r, l) in mission_skills.items()],
    ))

    db.add_all([
        Training(title="AWS & Kubernetes pour DevOps", skill_id=get_or_create_skill(db, "Kubernetes").id,
                 level="Avancé", duration_days=5, price=1500),
        Training(title="Terraform & Infrastructure as Code", skill_id=get_or_create_skill(db, "Terraform").id,
                 level="Intermédiaire", duration_days=3, price=900),
    ])
    db.commit()
