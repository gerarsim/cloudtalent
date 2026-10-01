from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import current_user, require_admin
from ..database import get_db
from ..models import Consultant, ConsultantSkill, User
from ..schemas import ConsultantIn, ConsultantOut, SkillLevelIn
from ..skills import get_or_create_skill
from .common import get_or_404

router = APIRouter(prefix="/consultants", tags=["Consultants"])


def _set_skills(db: Session, consultant: Consultant, skills: list[SkillLevelIn]) -> None:
    # Dédoublonnage après normalisation ("k8s" + "Kubernetes" -> une seule ligne, niveau max)
    levels: dict[int, int] = {}
    for s in skills:
        skill = get_or_create_skill(db, s.name)
        levels[skill.id] = max(levels.get(skill.id, 0), s.level)
    consultant.skills = [ConsultantSkill(skill_id=sid, level=lvl) for sid, lvl in levels.items()]


@contextmanager
def _unique_email(db: Session):
    try:
        yield
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Un consultant avec cet email existe déjà")


def _check_access(user: User, consultant_id: int) -> None:
    """Un admin accède à toutes les fiches, un consultant uniquement à la sienne."""
    if user.role != "admin" and user.consultant_id != consultant_id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez accéder qu'à votre propre fiche")


def _own_id(user: User) -> int:
    if user.consultant_id is None:
        raise HTTPException(status_code=404, detail="Aucune fiche consultant rattachée à ce compte")
    return user.consultant_id


@router.get("/", response_model=list[ConsultantOut], dependencies=[Depends(require_admin)])
def list_consultants(db: Session = Depends(get_db)):
    return db.scalars(select(Consultant).order_by(Consultant.id.desc())).all()


# /me est déclaré avant /{consultant_id} pour ne pas être capturé par ce dernier
@router.get("/me", response_model=ConsultantOut)
def get_my_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_consultant(_own_id(user), user, db)


@router.put("/me", response_model=ConsultantOut)
def update_my_profile(data: ConsultantIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return update_consultant(_own_id(user), data, user, db)


@router.get("/{consultant_id}", response_model=ConsultantOut)
def get_consultant(consultant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _check_access(user, consultant_id)
    return get_or_404(db, Consultant, consultant_id, "Consultant")


@router.post("/", response_model=ConsultantOut, status_code=201, dependencies=[Depends(require_admin)])
def create_consultant(data: ConsultantIn, db: Session = Depends(get_db)):
    with _unique_email(db):
        obj = Consultant(**data.model_dump(exclude={"skills"}))
        db.add(obj)
        _set_skills(db, obj, data.skills)
        db.commit()
    db.refresh(obj)
    return obj


@router.put("/{consultant_id}", response_model=ConsultantOut)
def update_consultant(
    consultant_id: int, data: ConsultantIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    _check_access(user, consultant_id)
    obj = get_or_404(db, Consultant, consultant_id, "Consultant")
    with _unique_email(db):
        for k, v in data.model_dump(exclude={"skills"}).items():
            setattr(obj, k, v)
        obj.skills.clear()
        db.flush()
        _set_skills(db, obj, data.skills)
        db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{consultant_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_consultant(consultant_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Consultant, consultant_id, "Consultant"))
    db.commit()
    return Response(status_code=204)
