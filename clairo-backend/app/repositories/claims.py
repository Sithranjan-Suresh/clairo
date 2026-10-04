from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Appeal, DenialClaim, Document, RiskScore, User
from app.models.user import ROLE_ADMIN

SORTABLE = {
    "id": DenialClaim.id,
    "created_at": DenialClaim.id,        # id is monotonic; created_at is date-only
    "risk_score": DenialClaim.risk_score,
    "payer": DenialClaim.payer,
    "status": DenialClaim.status,
}

RISK_BANDS = {"LOW": (None, 40), "MEDIUM": (40, 70), "HIGH": (70, None)}


def risk_level(score: Optional[float]) -> str:
    s = score or 0
    return "HIGH" if s >= 70 else "MEDIUM" if s >= 40 else "LOW"


def visibility_clause(user: User):
    """Admins see everything; everyone else sees their own claims plus the
    shared demo data (user_id IS NULL)."""
    if user.role == ROLE_ADMIN:
        return None
    return or_(DenialClaim.user_id == user.id, DenialClaim.user_id.is_(None))


def can_modify(claim: DenialClaim, user: User) -> bool:
    return user.role == ROLE_ADMIN or claim.user_id == user.id


def get_visible(db: Session, claim_id: int, user: User) -> Optional[DenialClaim]:
    stmt = select(DenialClaim).where(DenialClaim.id == claim_id).options(
        selectinload(DenialClaim.appeals), selectinload(DenialClaim.risk_scores),
        selectinload(DenialClaim.documents),
    )
    clause = visibility_clause(user)
    if clause is not None:
        stmt = stmt.where(clause)
    return db.scalar(stmt)


def list_claims(
    db: Session,
    user: User,
    *,
    payer: Optional[str] = None,
    classification: Optional[str] = None,
    status: Optional[str] = None,
    risk: Optional[str] = None,
    q: Optional[str] = None,
    sort_by: str = "id",
    order: str = "desc",
    limit: int = 20,
    offset: int = 0,
):
    filters = []
    clause = visibility_clause(user)
    if clause is not None:
        filters.append(clause)
    if payer:
        filters.append(DenialClaim.payer == payer)
    if classification:
        filters.append(DenialClaim.classification == classification)
    if status:
        filters.append(DenialClaim.status == status)
    if risk and risk.upper() in RISK_BANDS:
        low, high = RISK_BANDS[risk.upper()]
        if low is not None:
            filters.append(DenialClaim.risk_score >= low)
        if high is not None:
            filters.append(DenialClaim.risk_score < high)
    if q:
        like = f"%{q.strip()}%"
        filters.append(or_(
            DenialClaim.payer.ilike(like),
            DenialClaim.patient_id.ilike(like),
            DenialClaim.cpt_codes.ilike(like),
            DenialClaim.denial_reason.ilike(like),
        ))

    total = db.scalar(select(func.count(DenialClaim.id)).where(*filters)) or 0
    column = SORTABLE.get(sort_by, DenialClaim.id)
    ordering = column.asc() if order == "asc" else column.desc()
    # Tie-break on id so pagination is stable when many rows share a value.
    rows = db.scalars(
        select(DenialClaim).where(*filters)
        .order_by(ordering.nulls_last(), DenialClaim.id.desc())   # unscored rows always last
        .limit(limit).offset(offset)
    ).all()
    return rows, total


def create(db: Session, **fields) -> DenialClaim:
    claim = DenialClaim(created_at=datetime.now().strftime("%Y-%m-%d"), **fields)
    db.add(claim)
    db.flush()
    return claim


def add_document(db: Session, **fields) -> Document:
    doc = Document(**fields)
    db.add(doc)
    db.flush()
    return doc


def add_risk_score(db: Session, **fields) -> RiskScore:
    row = RiskScore(**fields)
    db.add(row)
    db.flush()
    return row


def add_appeal(db: Session, **fields) -> Appeal:
    row = Appeal(**fields)
    db.add(row)
    db.flush()
    return row
