from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import PayerPolicy, User
from app.rag.retriever import retrieve_policy
from app.schemas import PolicyOut
from app.security.auth import get_current_user

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[PolicyOut])
def list_policies(
    payer: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    stmt = select(PayerPolicy).order_by(PayerPolicy.payer, PayerPolicy.title)
    if payer:
        stmt = stmt.where(PayerPolicy.payer.ilike(payer))
    return db.scalars(stmt).all()


@router.get("/search")
@limiter.limit("30/minute")
def search_policies(
    request: Request,
    q: str = Query(..., min_length=3, max_length=300),
    payer: str = "",
    limit: int = Query(5, ge=1, le=10),
    _user: User = Depends(get_current_user),
):
    """Semantic search across the indexed payer policies."""
    return {"query": q, "payer": payer, "results": retrieve_policy(payer, q, top_k=limit)}
