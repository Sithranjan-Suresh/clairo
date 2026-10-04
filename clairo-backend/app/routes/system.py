from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.cache import cache
from app.database import get_db
from app.security.auth import require_admin_or_key

router = APIRouter(tags=["system"])


@router.get("/health")
def health(response: Response, db: Session = Depends(get_db)):
    """Liveness + dependency check, used by Render and docker healthchecks."""
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    if not db_ok:
        response.status_code = 503
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "cache": cache.backend}


@router.get("/metrics", dependencies=[Depends(require_admin_or_key)])
def metrics():
    """Prometheus exposition format (admin only: it reveals traffic shape)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
