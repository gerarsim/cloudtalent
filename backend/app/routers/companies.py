from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Company
from ..schemas import CompanyIn, CompanyOut
from .common import get_or_404

router = APIRouter(prefix="/companies", tags=["Entreprises"])


@router.get("/", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    return db.scalars(select(Company).order_by(Company.id.desc())).all()


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Company, company_id, "Entreprise")


@router.post("/", response_model=CompanyOut, status_code=201)
def create_company(data: CompanyIn, db: Session = Depends(get_db)):
    obj = Company(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, data: CompanyIn, db: Session = Depends(get_db)):
    obj = get_or_404(db, Company, company_id, "Entreprise")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: int, db: Session = Depends(get_db)):
    # Les missions liées sont conservées (company_id -> NULL, ON DELETE SET NULL)
    db.delete(get_or_404(db, Company, company_id, "Entreprise"))
    db.commit()
    return Response(status_code=204)
