from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.repositories import audit as audit_repo
from app.schemas import AuditOut, Page
from app.security.auth import require_admin

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=Page)
def list_audit_logs(
    action: Optional[str] = Query(None, max_length=60),
    user_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    rows, total = audit_repo.list_logs(db, action=action, user_id=user_id, limit=limit, offset=offset)
    return Page(items=[AuditOut.model_validate(r) for r in rows], total=total,
                limit=limit, offset=offset)
