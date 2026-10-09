"""Fiches de paie : l'admin les établit (calcul brut → net luxembourgeois, fiche officielle en
pièce jointe facultative), le consultant les consulte et les télécharge dans son espace."""
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import payroll, payslip_pdf
from ..auth import current_user, require_admin
from ..database import get_db
from ..models import Consultant, Payslip, User
from ..schemas import Period, PayrollOut, PayslipOut, TaxClass, monthly_salary
from .common import file_response, get_or_404, read_upload

router = APIRouter(prefix="/payslips", tags=["Fiches de paie"])

PAYSLIP_MAX_BYTES = 5 * 1024 * 1024
PAYSLIP_TYPES = {".pdf": "application/pdf"}


def _visible(q, user: User):
    if user.role == "admin":
        return q
    if user.role == "consultant":
        return q.where(Payslip.consultant_id == user.consultant_id)
    raise HTTPException(status_code=403, detail="Les fiches de paie sont réservées aux consultants et à l'admin")


def _get(db: Session, payslip_id: int, user: User) -> Payslip:
    obj = db.scalar(_visible(select(Payslip).where(Payslip.id == payslip_id), user))
    if obj is None:
        raise HTTPException(status_code=404, detail=f"Fiche de paie {payslip_id} introuvable")
    return obj


@router.get("/", response_model=list[PayslipOut])
def list_payslips(consultant_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = _visible(select(Payslip), user)
    if consultant_id is not None:
        q = q.where(Payslip.consultant_id == consultant_id)
    return db.scalars(q.order_by(Payslip.period.desc(), Payslip.id.desc())).unique().all()


@router.get("/simulate", response_model=PayrollOut, dependencies=[Depends(require_admin)])
def simulate(gross: Annotated[float, Query(ge=0, le=1_000_000)], tax_class: TaxClass = "1"):
    """Simulation brut → net au Luxembourg (indicative)."""
    return payroll.compute(gross, tax_class)


@router.post("/", response_model=PayslipOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_payslip(
    consultant_id: Annotated[int, Form()],
    period: Annotated[Period, Form(description="Mois de paie, AAAA-MM")],
    gross: Annotated[float | None, Form(ge=0, le=1_000_000, description="Salaire brut ; vide = salaire mensuel du consultant")] = None,
    tax_class: Annotated[TaxClass | None, Form(description="Vide = classe du consultant")] = None,
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    """Établit (ou recalcule) la fiche de paie du mois. Un PDF officiel peut être joint ;
    sans nouveau fichier, celui déjà joint est conservé."""
    c = get_or_404(db, Consultant, consultant_id, "Consultant")
    if gross is None:
        gross = monthly_salary(c.tjm, c.reserve_pct, c.days_per_month).salary
    tax_class = tax_class or c.tax_class
    upload = None
    if file is not None and file.filename:
        upload = await read_upload(file, PAYSLIP_TYPES, PAYSLIP_MAX_BYTES, "fiche de paie")

    obj = db.scalar(select(Payslip).where(Payslip.consultant_id == c.id, Payslip.period == period))
    if obj is None:
        obj = Payslip(consultant_id=c.id, period=period)
        db.add(obj)
    details = payroll.compute(gross, tax_class)
    obj.tax_class, obj.gross, obj.net, obj.details = tax_class, details["gross"], details["net"], details
    if upload is not None:
        obj.filename, obj.content_type, data = upload
        obj.size, obj.data = len(data), data
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{payslip_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_payslip(payslip_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Payslip, payslip_id, "Fiche de paie"))
    db.commit()
    return Response(status_code=204)


@router.get("/{payslip_id}/pdf")
def payslip_as_pdf(payslip_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Fiche de paie générée à partir du calcul enregistré."""
    obj = _get(db, payslip_id, user)
    pdf = payslip_pdf.render(obj.consultant.name, obj.consultant.title, obj.period, obj.details)
    return file_response(pdf, "application/pdf", f"fiche-de-paie-{obj.period}.pdf")


@router.get("/{payslip_id}/file")
def payslip_official_file(payslip_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Fiche officielle jointe par l'admin."""
    obj = _get(db, payslip_id, user)
    data = db.scalar(select(Payslip.data).where(Payslip.id == obj.id))
    if data is None:
        raise HTTPException(status_code=404, detail="Aucune fiche officielle jointe")
    return file_response(data, obj.content_type, obj.filename)
