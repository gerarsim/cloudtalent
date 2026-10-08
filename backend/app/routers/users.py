from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import hash_password, require_admin
from ..database import get_db
from ..models import Company, Consultant, User
from ..schemas import UserIn, UserOut, UserUpdate
from .common import get_or_404

# Gestion des comptes : réservée aux admins (dépendance au niveau du router)
router = APIRouter(prefix="/users", tags=["Utilisateurs"], dependencies=[Depends(require_admin)])


def _apply(db: Session, obj: User, data: UserIn | UserUpdate) -> None:
    if data.role == "consultant":
        if data.consultant_id is None:
            raise HTTPException(status_code=422, detail="Un compte consultant doit être rattaché à une fiche consultant")
        if db.get(Consultant, data.consultant_id) is None:
            raise HTTPException(status_code=422, detail=f"Consultant {data.consultant_id} introuvable")
    if data.role == "company":
        if data.company_id is None:
            raise HTTPException(status_code=422, detail="Un compte entreprise doit être rattaché à une entreprise")
        if db.get(Company, data.company_id) is None:
            raise HTTPException(status_code=422, detail=f"Entreprise {data.company_id} introuvable")
    obj.email = data.email.lower()
    obj.role = data.role
    obj.consultant_id = data.consultant_id if data.role == "consultant" else None
    obj.company_id = data.company_id if data.role == "company" else None
    obj.active = data.active
    if data.password:
        obj.password_hash = hash_password(data.password)


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email déjà utilisé, ou consultant déjà rattaché à un compte")


@router.get("/", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).unique().all()


@router.post("/", response_model=UserOut, status_code=201)
def create_user(data: UserIn, db: Session = Depends(get_db)):
    obj = User()
    _apply(db, obj, data)
    db.add(obj)
    _commit(db)
    db.refresh(obj)
    return obj


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), me: User = Depends(require_admin)):
    obj = get_or_404(db, User, user_id, "Utilisateur")
    if obj.id == me.id and (data.role != "admin" or not data.active):
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas retirer vos propres droits admin")
    _apply(db, obj, data)
    _commit(db)
    db.refresh(obj)
    return obj


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), me: User = Depends(require_admin)):
    obj = get_or_404(db, User, user_id, "Utilisateur")
    if obj.id == me.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte")
    db.delete(obj)
    db.commit()
    return Response(status_code=204)
