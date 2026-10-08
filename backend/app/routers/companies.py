from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user, require_admin
from ..database import get_db
from ..models import Company, User
from ..schemas import CompanyIn, CompanyOut
from .common import get_or_404

router = APIRouter(prefix="/companies", tags=["Entreprises"])


def own_company_id(user: User) -> int:
    if user.role != "company":
        raise HTTPException(status_code=403, detail="Réservé aux comptes entreprise")
    if user.company_id is None:
        raise HTTPException(status_code=404, detail="Aucune entreprise rattachée à ce compte")
    return user.company_id


# Entreprise partenaire : sa propre fiche uniquement (/me déclaré avant /{company_id})
@router.get("/me", response_model=CompanyOut)
def get_my_company(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_or_404(db, Company, own_company_id(user), "Entreprise")


@router.put("/me", response_model=CompanyOut)
def update_my_company(data: CompanyIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _update(db, get_or_404(db, Company, own_company_id(user), "Entreprise"), data)


def _update(db: Session, obj: Company, data: CompanyIn) -> Company:
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


# Le reste est réservé aux admins
@router.get("/", response_model=list[CompanyOut], dependencies=[Depends(require_admin)])
def list_companies(db: Session = Depends(get_db)):
    return db.scalars(select(Company).order_by(Company.id.desc())).all()


@router.get("/{company_id}", response_model=CompanyOut, dependencies=[Depends(require_admin)])
def get_company(company_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Company, company_id, "Entreprise")


@router.post("/", response_model=CompanyOut, status_code=201, dependencies=[Depends(require_admin)])
def create_company(data: CompanyIn, db: Session = Depends(get_db)):
    obj = Company(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{company_id}", response_model=CompanyOut, dependencies=[Depends(require_admin)])
def update_company(company_id: int, data: CompanyIn, db: Session = Depends(get_db)):
    return _update(db, get_or_404(db, Company, company_id, "Entreprise"), data)


@router.delete("/{company_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_company(company_id: int, db: Session = Depends(get_db)):
    # Les missions liées sont conservées (company_id -> NULL, ON DELETE SET NULL) ;
    # les comptes de l'entreprise sont supprimés (ON DELETE CASCADE)
    db.delete(get_or_404(db, Company, company_id, "Entreprise"))
    db.commit()
    return Response(status_code=204)
