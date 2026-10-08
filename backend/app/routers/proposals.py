"""Consultants proposés par CloudTalent aux entreprises partenaires, mission par mission.

L'admin propose, l'entreprise consulte le profil (sans données financières) et le CV,
puis retient ou refuse."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import require_admin, require_admin_or_company
from ..database import get_db
from ..models import Consultant, Mission, Proposal, User
from ..schemas import ProposalIn, ProposalOut, ProposalStatusIn
from .common import get_or_404
from .consultants import cv_response

router = APIRouter(prefix="/proposals", tags=["Propositions"])


def _get(db: Session, proposal_id: int, user: User) -> Proposal:
    obj = get_or_404(db, Proposal, proposal_id, "Proposition")
    if user.role == "company" and obj.mission.company_id != user.company_id:
        raise HTTPException(status_code=404, detail=f"Proposition {proposal_id} introuvable")
    return obj


@router.get("/", response_model=list[ProposalOut])
def list_proposals(mission_id: int | None = None, db: Session = Depends(get_db),
                   user: User = Depends(require_admin_or_company)):
    q = select(Proposal).join(Proposal.mission).order_by(Proposal.id.desc())
    if user.role == "company":
        q = q.where(Mission.company_id == user.company_id)
    if mission_id is not None:
        q = q.where(Proposal.mission_id == mission_id)
    return db.scalars(q).unique().all()


@router.post("/", response_model=ProposalOut, status_code=201, dependencies=[Depends(require_admin)])
def create_proposal(data: ProposalIn, db: Session = Depends(get_db)):
    if db.get(Mission, data.mission_id) is None:
        raise HTTPException(status_code=422, detail=f"Mission {data.mission_id} introuvable")
    if db.get(Consultant, data.consultant_id) is None:
        raise HTTPException(status_code=422, detail=f"Consultant {data.consultant_id} introuvable")
    obj = Proposal(mission_id=data.mission_id, consultant_id=data.consultant_id)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ce consultant est déjà proposé pour cette mission")
    db.refresh(obj)
    return obj


@router.put("/{proposal_id}", response_model=ProposalOut)
def update_proposal(proposal_id: int, data: ProposalStatusIn, db: Session = Depends(get_db),
                    user: User = Depends(require_admin_or_company)):
    """L'entreprise retient ou refuse le consultant (l'admin peut aussi corriger le statut)."""
    obj = _get(db, proposal_id, user)
    obj.status = data.status
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{proposal_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_proposal(proposal_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Proposal, proposal_id, "Proposition"))
    db.commit()
    return Response(status_code=204)


@router.get("/{proposal_id}/cv")
def download_proposal_cv(proposal_id: int, db: Session = Depends(get_db),
                         user: User = Depends(require_admin_or_company)):
    """CV du consultant proposé : l'entreprise n'y accède que via une proposition sur ses missions."""
    return cv_response(db, _get(db, proposal_id, user).consultant_id)
