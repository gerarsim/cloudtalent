from contextlib import contextmanager

from pathlib import PurePath
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, undefer

from ..auth import current_user, require_admin
from ..database import get_db
from ..models import Consultant, ConsultantCV, ConsultantSkill, Mission, User
from ..schemas import ConsultantIn, ConsultantOut, ConsultantSelfIn, SkillLevelIn
from ..skills import get_or_create_skill
from .common import get_or_404

router = APIRouter(prefix="/consultants", tags=["Consultants"])

CV_MAX_BYTES = 5 * 1024 * 1024
CV_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odt": "application/vnd.oasis.opendocument.text",
}


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


def _check_mission(db: Session, mission_id: int | None) -> None:
    if mission_id is not None and db.get(Mission, mission_id) is None:
        raise HTTPException(status_code=422, detail=f"Mission {mission_id} introuvable")


def _apply(db: Session, obj: Consultant, data: ConsultantSelfIn) -> Consultant:
    with _unique_email(db):
        for k, v in data.model_dump(exclude={"skills"}).items():
            setattr(obj, k, v)
        obj.skills.clear()
        db.flush()
        _set_skills(db, obj, data.skills)
        db.commit()
    db.refresh(obj)
    return obj


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
def update_my_profile(data: ConsultantSelfIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Le consultant ne modifie que réserve, jours facturés, profil, compétences et disponibilité."""
    return _apply(db, get_or_404(db, Consultant, _own_id(user), "Consultant"), data)


@router.put("/me/cv", response_model=ConsultantOut)
async def upload_my_cv(file: UploadFile, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return await upload_cv(_own_id(user), file, user, db)


@router.get("/me/cv")
def download_my_cv(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return download_cv(_own_id(user), user, db)


@router.delete("/me/cv", status_code=204)
def delete_my_cv(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return delete_cv(_own_id(user), user, db)


@router.get("/{consultant_id}", response_model=ConsultantOut)
def get_consultant(consultant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _check_access(user, consultant_id)
    return get_or_404(db, Consultant, consultant_id, "Consultant")


@router.post("/", response_model=ConsultantOut, status_code=201, dependencies=[Depends(require_admin)])
def create_consultant(data: ConsultantIn, db: Session = Depends(get_db)):
    _check_mission(db, data.mission_id)
    with _unique_email(db):
        obj = Consultant(**data.model_dump(exclude={"skills"}))
        db.add(obj)
        _set_skills(db, obj, data.skills)
        db.commit()
    db.refresh(obj)
    return obj


@router.put("/{consultant_id}", response_model=ConsultantOut, dependencies=[Depends(require_admin)])
def update_consultant(consultant_id: int, data: ConsultantIn, db: Session = Depends(get_db)):
    obj = get_or_404(db, Consultant, consultant_id, "Consultant")
    _check_mission(db, data.mission_id)
    return _apply(db, obj, data)


@router.delete("/{consultant_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_consultant(consultant_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Consultant, consultant_id, "Consultant"))
    db.commit()
    return Response(status_code=204)


# --- CV ----------------------------------------------------------------------

@router.put("/{consultant_id}/cv", response_model=ConsultantOut)
async def upload_cv(consultant_id: int, file: UploadFile, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    """Envoie (ou remplace) le CV : PDF, DOC, DOCX ou ODT, 5 Mo maximum."""
    _check_access(user, consultant_id)
    obj = get_or_404(db, Consultant, consultant_id, "Consultant")
    filename = PurePath(file.filename or "").name[:200]
    content_type = CV_TYPES.get(PurePath(filename).suffix.lower())
    if content_type is None:
        raise HTTPException(status_code=422, detail="Format de CV accepté : PDF, DOC, DOCX ou ODT")
    data = await file.read(CV_MAX_BYTES + 1)
    if len(data) > CV_MAX_BYTES:
        raise HTTPException(status_code=413, detail="CV trop volumineux (5 Mo maximum)")
    if not data:
        raise HTTPException(status_code=422, detail="Fichier vide")
    obj.cv = ConsultantCV(filename=filename, content_type=content_type, size=len(data), data=data)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{consultant_id}/cv")
def download_cv(consultant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _check_access(user, consultant_id)
    return cv_response(db, consultant_id)


def cv_response(db: Session, consultant_id: int) -> Response:
    """Téléchargement du CV (droits vérifiés par l'appelant)."""
    cv = db.scalar(select(ConsultantCV).options(undefer(ConsultantCV.data))
                   .where(ConsultantCV.consultant_id == consultant_id))
    if cv is None:
        raise HTTPException(status_code=404, detail="Aucun CV")
    # Le type vient de notre liste blanche, jamais du client ; nosniff empêche le navigateur de deviner
    return Response(cv.data, media_type=cv.content_type, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(cv.filename)}",
        "X-Content-Type-Options": "nosniff",
    })


@router.delete("/{consultant_id}/cv", status_code=204)
def delete_cv(consultant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _check_access(user, consultant_id)
    obj = get_or_404(db, Consultant, consultant_id, "Consultant")
    obj.cv = None
    db.commit()
    return Response(status_code=204)
