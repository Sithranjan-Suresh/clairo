from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.config import MAX_UPLOAD_BYTES
from app.database import get_db
from app.limiter import limiter
from app.models import User
from app.models.claim import CLAIM_STATUSES
from app.repositories import audit as audit_repo
from app.repositories import claims as claims_repo
from app.schemas import AuditOut, ClaimDetail, ClaimSummary, Page
from app.security.auth import get_current_user
from app.services import claim_service

router = APIRouter(prefix="/claims", tags=["claims"])


def _get_claim(db: Session, claim_id: int, user: User):
    claim = claims_repo.get_visible(db, claim_id, user)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return claim


def _get_modifiable_claim(db: Session, claim_id: int, user: User):
    claim = _get_claim(db, claim_id, user)
    if not claims_repo.can_modify(claim, user):
        raise HTTPException(status_code=403, detail="You can view this claim but not modify it.")
    return claim


@router.post("", status_code=202)
@limiter.limit("10/minute")
async def create_claim(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a denial PDF. Analysis runs in the background — poll the job."""
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    claim, job = claim_service.create_claim_from_upload(
        db, user, filename=file.filename, content_type=file.content_type,
        content=content, request=request,
    )
    return {"claim_id": claim.id, "job_id": job.id, "status": claim.status}


@router.get("", response_model=Page)
def list_claims(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    payer: Optional[str] = None,
    classification: Optional[str] = None,
    status: Optional[str] = Query(None, description=f"One of {', '.join(CLAIM_STATUSES)}"),
    risk: Optional[str] = Query(None, description="LOW, MEDIUM or HIGH"),
    q: Optional[str] = Query(None, max_length=100, description="Search payer/patient/CPT/reason"),
    sort_by: str = Query("id", pattern="^(id|created_at|risk_score|payer|status)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    rows, total = claims_repo.list_claims(
        db, user, payer=payer, classification=classification, status=status, risk=risk,
        q=q, sort_by=sort_by, order=order, limit=limit, offset=offset,
    )
    items = [ClaimSummary(**claim_service.to_summary(c)) for c in rows]
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{claim_id}", response_model=ClaimDetail)
def get_claim(claim_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return claim_service.to_detail(_get_claim(db, claim_id, user))


@router.post("/{claim_id}/analyze", status_code=202)
@limiter.limit("10/minute")
def reanalyze_claim(
    request: Request, claim_id: int,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    claim = _get_modifiable_claim(db, claim_id, user)
    job = claim_service.enqueue_analysis(db, claim, user, request)
    return {"claim_id": claim.id, "job_id": job.id}


@router.post("/{claim_id}/appeal", status_code=202)
@limiter.limit("10/minute")
def create_appeal(
    request: Request, claim_id: int,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    claim = _get_modifiable_claim(db, claim_id, user)
    if not claim.classification:
        raise HTTPException(status_code=409, detail="Claim hasn't been analyzed yet.")
    job = claim_service.enqueue_appeal(db, claim, user, request)
    return {"claim_id": claim.id, "job_id": job.id}


@router.get("/{claim_id}/audit", response_model=list[AuditOut])
def claim_audit(claim_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_claim(db, claim_id, user)
    return audit_repo.for_claim(db, claim_id)
