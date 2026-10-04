"""Postgres-backed job queue.

Workers claim rows with SELECT ... FOR UPDATE SKIP LOCKED, so any number of
worker processes can poll the same table without double-processing a job and
without blocking each other. SQLite ignores the lock clause, which is fine
for single-process development.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job
from app.models.base import utcnow
from app.models.job import JOB_FAILED, JOB_QUEUED, JOB_RUNNING, JOB_SUCCEEDED


def enqueue(
    db: Session,
    job_type: str,
    *,
    claim_id: Optional[int] = None,
    user_id: Optional[int] = None,
    payload: Optional[dict] = None,
    max_attempts: int = 3,
) -> Job:
    job = Job(
        id=uuid.uuid4().hex, type=job_type, claim_id=claim_id, user_id=user_id,
        payload=payload or {}, max_attempts=max_attempts, status=JOB_QUEUED,
        attempts=0, run_after=utcnow(), created_at=utcnow(),
    )
    db.add(job)
    db.flush()
    return job


def get(db: Session, job_id: str) -> Optional[Job]:
    return db.get(Job, job_id)


def claim_next(db: Session) -> Optional[Job]:
    """Atomically take the oldest runnable job and mark it running."""
    job = db.scalar(
        select(Job)
        .where(Job.status == JOB_QUEUED, Job.run_after <= utcnow())
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None
    job.status = JOB_RUNNING
    job.attempts += 1
    job.started_at = utcnow()
    db.commit()
    return job


def mark_succeeded(db: Session, job: Job, result: dict) -> None:
    job.status = JOB_SUCCEEDED
    job.result = result
    job.error = None
    job.finished_at = utcnow()
    db.commit()


def mark_retry(db: Session, job: Job, error: str, delay_seconds: float) -> None:
    job.status = JOB_QUEUED
    job.error = error
    job.run_after = utcnow() + timedelta(seconds=delay_seconds)
    db.commit()


def mark_failed(db: Session, job: Job, error: str) -> None:
    job.status = JOB_FAILED
    job.error = error
    job.finished_at = utcnow()
    db.commit()


def requeue_stale(db: Session, older_than: timedelta = timedelta(minutes=10)) -> int:
    """A worker that died mid-job leaves it 'running' forever; put those back."""
    cutoff: datetime = utcnow() - older_than
    stale = db.scalars(
        select(Job).where(Job.status == JOB_RUNNING, Job.started_at < cutoff)
        .with_for_update(skip_locked=True)
    ).all()
    for job in stale:
        job.status = JOB_QUEUED
        job.error = "worker lost; requeued"
    db.commit()
    return len(stale)
