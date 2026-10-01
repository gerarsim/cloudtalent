"""Normalisation des compétences et résolution vers le référentiel `skills`."""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Skill

# Synonymes courants -> nom canonique. Clés déjà normalisées (voir slugify).
ALIASES: dict[str, str] = {
    "k8s": "Kubernetes",
    "kube": "Kubernetes",
    "tf": "Terraform",
    "amazon web services": "AWS",
    "aws eks": "EKS",
    "amazon eks": "EKS",
    "azure kubernetes service": "AKS",
    "gitlab ci": "GitLab CI/CD",
    "gitlab-ci": "GitLab CI/CD",
    "gitlab cicd": "GitLab CI/CD",
    "github action": "GitHub Actions",
    "gh actions": "GitHub Actions",
    "argo cd": "ArgoCD",
    "argo-cd": "ArgoCD",
    "gcp": "Google Cloud",
    "google cloud platform": "Google Cloud",
    "postgres": "PostgreSQL",
    "js": "JavaScript",
    "ts": "TypeScript",
}

CATEGORIES: dict[str, str] = {
    "aws": "Cloud", "azure": "Cloud", "google cloud": "Cloud",
    "eks": "Conteneurs", "aks": "Conteneurs", "kubernetes": "Conteneurs",
    "docker": "Conteneurs", "helm": "Conteneurs", "openshift": "Conteneurs",
    "terraform": "IaC", "ansible": "IaC", "pulumi": "IaC", "cloudformation": "IaC",
    "gitlab ci/cd": "CI/CD", "github actions": "CI/CD", "jenkins": "CI/CD",
    "argocd": "CI/CD", "azure devops": "CI/CD",
    "linux": "Système", "powershell": "Système", "python": "Langage", "go": "Langage",
    "devsecops": "Sécurité",
}

_WS = re.compile(r"\s+")


def slugify(name: str) -> str:
    """'  GitLab   CI ' -> 'gitlab ci'. Comparaison insensible à la casse et aux espaces."""
    return _WS.sub(" ", name.strip().lower())


def canonical(name: str) -> tuple[str, str]:
    """Retourne (nom affiché, slug) après application des synonymes."""
    slug = slugify(name)
    if slug in ALIASES:
        display = ALIASES[slug]
        return display, slugify(display)
    return _WS.sub(" ", name.strip()), slug


def get_or_create_skill(db: Session, name: str) -> Skill:
    display, slug = canonical(name)
    if not slug:
        raise ValueError("Nom de compétence vide")
    skill = db.scalar(select(Skill).where(Skill.slug == slug))
    if skill is None:
        skill = Skill(name=display, slug=slug, category=CATEGORIES.get(slug, ""))
        db.add(skill)
        db.flush()
    return skill
