from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.user import ROLE_ADMIN
from app.repositories import jobs as jobs_repo
from app.schemas import JobOut
from app.security.auth import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = jobs_repo.get(db, job_id)
    # 404 (not 403) for other people's jobs so job IDs can't be probed.
    if job is None or (user.role != ROLE_ADMIN and job.user_id != user.id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobOut(
        id=job.id, type=job.type, status=job.status, claim_id=job.claim_id,
        attempts=job.attempts, error=job.error, result=job.result,
        created_at=job.created_at, finished_at=job.finished_at,
    )
