"""Inscriptions aux formations CloudTalent par les entreprises partenaires.

L'entreprise inscrit ses collaborateurs (demande) et peut annuler ; l'admin confirme."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_admin_or_company
from ..database import get_db
from ..models import Enrollment, Training, User
from ..schemas import EnrollmentIn, EnrollmentOut, EnrollmentStatusIn
from .common import get_or_404

router = APIRouter(prefix="/enrollments", tags=["Inscriptions"])


@router.get("/", response_model=list[EnrollmentOut])
def list_enrollments(training_id: int | None = None, db: Session = Depends(get_db),
                     user: User = Depends(require_admin_or_company)):
    q = select(Enrollment).order_by(Enrollment.id.desc())
    if user.role == "company":
        q = q.where(Enrollment.company_id == user.company_id)
    if training_id is not None:
        q = q.where(Enrollment.training_id == training_id)
    return db.scalars(q).unique().all()


@router.post("/", response_model=EnrollmentOut, status_code=201)
def create_enrollment(data: EnrollmentIn, db: Session = Depends(get_db),
                      user: User = Depends(require_admin_or_company)):
    if user.role != "company":
        raise HTTPException(status_code=403, detail="Les inscriptions sont faites par les entreprises partenaires")
    if db.get(Training, data.training_id) is None:
        raise HTTPException(status_code=422, detail=f"Formation {data.training_id} introuvable")
    obj = Enrollment(training_id=data.training_id, company_id=user.company_id,
                     participant_name=data.participant_name, participant_email=data.participant_email.lower())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{enrollment_id}", response_model=EnrollmentOut)
def update_enrollment(enrollment_id: int, data: EnrollmentStatusIn, db: Session = Depends(get_db),
                      user: User = Depends(require_admin_or_company)):
    obj = get_or_404(db, Enrollment, enrollment_id, "Inscription")
    if user.role == "company":
        if obj.company_id != user.company_id:
            raise HTTPException(status_code=404, detail=f"Inscription {enrollment_id} introuvable")
        if data.status != "Annulée":
            raise HTTPException(status_code=403, detail="Seul CloudTalent confirme une inscription")
    obj.status = data.status
    db.commit()
    db.refresh(obj)
    return obj
