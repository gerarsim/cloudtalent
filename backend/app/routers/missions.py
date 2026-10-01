from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..matching import rank
from ..models import Company, Consultant, Mission, MissionSkill
from ..schemas import MatchOut, MissionIn, MissionOut, MissionSkillIn
from ..skills import get_or_create_skill
from .common import get_or_404

router = APIRouter(prefix="/missions", tags=["Missions"])


def _check_company(db: Session, company_id: int | None) -> None:
    if company_id is not None and db.get(Company, company_id) is None:
        raise HTTPException(status_code=422, detail=f"Entreprise {company_id} introuvable")


def _set_skills(db: Session, mission: Mission, skills: list[MissionSkillIn]) -> None:
    merged: dict[int, MissionSkill] = {}
    for s in skills:
        skill = get_or_create_skill(db, s.name)
        if skill.id in merged:  # doublon après normalisation : on garde le plus exigeant
            prev = merged[skill.id]
            prev.required = prev.required or s.required
            prev.min_level = max(prev.min_level, s.min_level)
        else:
            merged[skill.id] = MissionSkill(skill_id=skill.id, required=s.required, min_level=s.min_level)
    mission.skills = list(merged.values())


@router.get("/", response_model=list[MissionOut])
def list_missions(status: str | None = None, db: Session = Depends(get_db)):
    q = select(Mission).order_by(Mission.id.desc())
    if status:
        q = q.where(Mission.status == status)
    return db.scalars(q).unique().all()


@router.get("/{mission_id}", response_model=MissionOut)
def get_mission(mission_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Mission, mission_id, "Mission")


@router.post("/", response_model=MissionOut, status_code=201)
def create_mission(data: MissionIn, db: Session = Depends(get_db)):
    _check_company(db, data.company_id)
    obj = Mission(**data.model_dump(exclude={"skills"}))
    db.add(obj)
    _set_skills(db, obj, data.skills)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{mission_id}", response_model=MissionOut)
def update_mission(mission_id: int, data: MissionIn, db: Session = Depends(get_db)):
    obj = get_or_404(db, Mission, mission_id, "Mission")
    _check_company(db, data.company_id)
    for k, v in data.model_dump(exclude={"skills"}).items():
        setattr(obj, k, v)
    obj.skills.clear()
    db.flush()
    _set_skills(db, obj, data.skills)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{mission_id}", status_code=204)
def delete_mission(mission_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Mission, mission_id, "Mission"))
    db.commit()
    return Response(status_code=204)


@router.get("/{mission_id}/matches", response_model=list[MatchOut])
def matches(
    mission_id: int,
    min_score: int = Query(0, ge=0, le=100),
    only_eligible: bool = False,
    db: Session = Depends(get_db),
):
    """Consultants classés pour la mission. Toujours une liste de MatchOut (vide si
    la mission n'a pas de compétences)."""
    mission = get_or_404(db, Mission, mission_id, "Mission")
    consultants = db.scalars(select(Consultant)).all()
    return [
        m for m in rank(mission, consultants)
        if m.score >= min_score and (m.eligible or not only_eligible)
    ]
