from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Training
from ..schemas import TrainingIn, TrainingOut
from ..skills import get_or_create_skill
from .common import get_or_404

router = APIRouter(prefix="/trainings", tags=["Formations"])


def _apply(db: Session, obj: Training, data: TrainingIn) -> None:
    for k, v in data.model_dump(exclude={"skill"}).items():
        setattr(obj, k, v)
    obj.skill_id = get_or_create_skill(db, data.skill).id if data.skill else None


@router.get("/", response_model=list[TrainingOut])
def list_trainings(db: Session = Depends(get_db)):
    return db.scalars(select(Training).order_by(Training.id.desc())).unique().all()


@router.get("/{training_id}", response_model=TrainingOut)
def get_training(training_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Training, training_id, "Formation")


@router.post("/", response_model=TrainingOut, status_code=201)
def create_training(data: TrainingIn, db: Session = Depends(get_db)):
    obj = Training()
    _apply(db, obj, data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{training_id}", response_model=TrainingOut)
def update_training(training_id: int, data: TrainingIn, db: Session = Depends(get_db)):
    obj = get_or_404(db, Training, training_id, "Formation")
    _apply(db, obj, data)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{training_id}", status_code=204)
def delete_training(training_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Training, training_id, "Formation"))
    db.commit()
    return Response(status_code=204)
