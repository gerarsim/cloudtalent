from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_admin, require_admin_or_company
from ..database import get_db
from ..matching import rank
from ..models import Company, Consultant, Mission, MissionSkill, User
from ..schemas import MatchOut, MissionIn, MissionOut, MissionSkillIn
from ..skills import get_or_create_skill
from .common import get_or_404

# Admin : toutes les missions. Entreprise partenaire : uniquement les siennes.
router = APIRouter(prefix="/missions", tags=["Missions"])


def _get(db: Session, mission_id: int, user: User) -> Mission:
    obj = get_or_404(db, Mission, mission_id, "Mission")
    if user.role == "company" and obj.company_id != user.company_id:
        # 404 plutôt que 403 : une entreprise n'a pas à savoir quelles missions existent ailleurs
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} introuvable")
    return obj


def _admin_only(user: User) -> set[str]:
    """Champs ignorés à l'écriture : company_id est traité à part, le TJM consultant est réservé à l'admin."""
    return {"skills", "company_id"} | ({"consultant_tjm"} if user.role == "company" else set())


def _out(obj: Mission, user: User) -> MissionOut:
    """Le TJM proposé au consultant n'est jamais montré à l'entreprise."""
    out = MissionOut.model_validate(obj)
    if user.role == "company":
        out.consultant_tjm = out.offered_tjm = None
    return out


def _company_id(db: Session, data: MissionIn, user: User) -> int | None:
    """Une entreprise publie toujours pour elle-même, quel que soit le company_id envoyé."""
    if user.role == "company":
        return user.company_id
    _check_company(db, data.company_id)
    return data.company_id


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
def list_missions(status: str | None = None, db: Session = Depends(get_db),
                  user: User = Depends(require_admin_or_company)):
    q = select(Mission).order_by(Mission.id.desc())
    if user.role == "company":
        q = q.where(Mission.company_id == user.company_id)
    if status:
        q = q.where(Mission.status == status)
    return [_out(m, user) for m in db.scalars(q).unique().all()]


@router.get("/{mission_id}", response_model=MissionOut)
def get_mission(mission_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin_or_company)):
    return _out(_get(db, mission_id, user), user)


@router.post("/", response_model=MissionOut, status_code=201)
def create_mission(data: MissionIn, db: Session = Depends(get_db), user: User = Depends(require_admin_or_company)):
    obj = Mission(**data.model_dump(exclude=_admin_only(user)), company_id=_company_id(db, data, user))
    db.add(obj)
    _set_skills(db, obj, data.skills)
    db.commit()
    db.refresh(obj)
    return _out(obj, user)


@router.put("/{mission_id}", response_model=MissionOut)
def update_mission(mission_id: int, data: MissionIn, db: Session = Depends(get_db),
                   user: User = Depends(require_admin_or_company)):
    obj = _get(db, mission_id, user)
    obj.company_id = _company_id(db, data, user)
    for k, v in data.model_dump(exclude=_admin_only(user)).items():
        setattr(obj, k, v)
    obj.skills.clear()
    db.flush()
    _set_skills(db, obj, data.skills)
    db.commit()
    db.refresh(obj)
    return _out(obj, user)


@router.delete("/{mission_id}", status_code=204)
def delete_mission(mission_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin_or_company)):
    db.delete(_get(db, mission_id, user))
    db.commit()
    return Response(status_code=204)


# Matching : données consultants (TJM, réserve…), réservé aux admins
@router.get("/{mission_id}/matches", response_model=list[MatchOut], dependencies=[Depends(require_admin)])
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
