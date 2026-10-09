"""Factures mensuelles signées par le consultant et son client.

Le consultant dépose sa facture (PDF ou scan) pour un mois ; l'admin la voit, demande le
paiement à l'entreprise cliente puis la marque payée ; l'entreprise voit les factures dont
le paiement lui est demandé. Les montants exposés dépendent du rôle (voir InvoiceOut)."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user, require_admin
from ..database import get_db
from ..models import Consultant, Invoice, Mission, User
from ..schemas import InvoiceOut, InvoiceStatusIn, Period
from .common import file_response, get_or_404, read_upload

router = APIRouter(prefix="/invoices", tags=["Factures"])

INVOICE_MAX_BYTES = 10 * 1024 * 1024
INVOICE_TYPES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
# Champs financiers visibles par rôle ; les autres sont mis à null
VISIBLE = {
    "admin": {"consultant_tjm", "consultant_amount", "billing_tjm", "amount", "margin"},
    "consultant": {"consultant_tjm", "consultant_amount"},
    "company": {"billing_tjm", "amount"},
}
MONEY = {"consultant_tjm", "consultant_amount", "billing_tjm", "amount", "margin"}


def _out(obj: Invoice, user: User) -> InvoiceOut:
    out = InvoiceOut.model_validate(obj)
    return out.model_copy(update={k: None for k in MONEY - VISIBLE[user.role]})


def _visible(q, user: User):
    """Admin : tout. Consultant : ses factures. Entreprise : celles de ses missions dont le paiement est demandé."""
    if user.role == "consultant":
        return q.where(Invoice.consultant_id == user.consultant_id)
    if user.role == "company":
        return q.join(Invoice.mission).where(Mission.company_id == user.company_id, Invoice.status != "Déposée")
    return q


def _get(db: Session, invoice_id: int, user: User) -> Invoice:
    obj = db.scalar(_visible(select(Invoice).where(Invoice.id == invoice_id), user))
    if obj is None:
        raise HTTPException(status_code=404, detail=f"Facture {invoice_id} introuvable")
    return obj


@router.get("/", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = _visible(select(Invoice), user).order_by(Invoice.period.desc(), Invoice.id.desc())
    return [_out(i, user) for i in db.scalars(q).unique().all()]


@router.post("/", response_model=InvoiceOut, status_code=201)
async def upload_invoice(
    file: UploadFile,
    period: Annotated[Period, Form(description="Mois facturé, AAAA-MM")],
    days: Annotated[float, Form(gt=0, le=31, description="Jours travaillés dans le mois")],
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Le consultant dépose sa facture signée (PDF, JPG ou PNG, 10 Mo). Un nouveau dépôt pour le
    même mois remplace le précédent tant que le paiement n'a pas été demandé."""
    if user.role != "consultant" or user.consultant_id is None:
        raise HTTPException(status_code=403, detail="Les factures sont déposées par les consultants")
    me = get_or_404(db, Consultant, user.consultant_id, "Consultant")
    filename, content_type, data = await read_upload(file, INVOICE_TYPES, INVOICE_MAX_BYTES, "facture")
    obj = db.scalar(select(Invoice).where(Invoice.consultant_id == me.id, Invoice.period == period))
    if obj is not None and obj.status != "Déposée":
        raise HTTPException(status_code=409, detail="Le paiement de ce mois est déjà demandé : la facture ne peut plus être remplacée")
    if obj is None:
        obj = Invoice(consultant_id=me.id, period=period)
        db.add(obj)
    # Tarifs figés au dépôt
    obj.mission_id, obj.days = me.mission_id, days
    obj.consultant_tjm, obj.billing_tjm = me.tjm, me.effective_billing_tjm
    obj.filename, obj.content_type, obj.size, obj.data = filename, content_type, len(data), data
    obj.uploaded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return _out(obj, user)


@router.put("/{invoice_id}", response_model=InvoiceOut, dependencies=[Depends(require_admin)])
def update_invoice(invoice_id: int, data: InvoiceStatusIn, db: Session = Depends(get_db),
                   user: User = Depends(require_admin)):
    """Admin : « Paiement demandé » rend la facture visible à l'entreprise cliente, puis « Payée »."""
    obj = get_or_404(db, Invoice, invoice_id, "Facture")
    if data.status == "Paiement demandé":
        if obj.mission is None or obj.mission.company_id is None:
            raise HTTPException(status_code=422, detail="Facture sans mission ni entreprise cliente : impossible de demander le paiement")
        if obj.billing_tjm is None:
            raise HTTPException(status_code=422, detail="TJM client inconnu : renseignez-le sur la fiche consultant puis faites redéposer la facture")
    now = datetime.now(timezone.utc)
    obj.status = data.status
    obj.requested_at = now if data.status == "Paiement demandé" else (obj.requested_at if data.status == "Payée" else None)
    obj.paid_at = now if data.status == "Payée" else None
    db.commit()
    db.refresh(obj)
    return _out(obj, user)


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Le consultant retire sa facture tant que le paiement n'est pas demandé ; l'admin toujours."""
    obj = _get(db, invoice_id, user)
    if user.role == "company" or (user.role == "consultant" and obj.status != "Déposée"):
        raise HTTPException(status_code=403, detail="Cette facture ne peut plus être supprimée")
    db.delete(obj)
    db.commit()
    return Response(status_code=204)


@router.get("/{invoice_id}/file")
def download_invoice(invoice_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    obj = _get(db, invoice_id, user)
    data = db.scalar(select(Invoice.data).where(Invoice.id == obj.id))
    return file_response(data, obj.content_type, obj.filename)
