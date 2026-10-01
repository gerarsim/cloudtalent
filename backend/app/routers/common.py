from typing import TypeVar

from fastapi import HTTPException
from sqlalchemy.orm import Session

T = TypeVar("T")


def get_or_404(db: Session, model: type[T], obj_id: int, label: str) -> T:
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} {obj_id} introuvable")
    return obj
