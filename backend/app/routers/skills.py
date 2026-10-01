from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Skill
from ..schemas import SkillOut

router = APIRouter(prefix="/skills", tags=["Compétences"])


@router.get("/", response_model=list[SkillOut])
def list_skills(q: str | None = None, db: Session = Depends(get_db)):
    """Référentiel des compétences (autocomplétion côté frontend)."""
    query = select(Skill).order_by(Skill.name)
    if q:
        query = query.where(Skill.slug.contains(q.strip().lower()))
    return db.scalars(query).all()
