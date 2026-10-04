from datetime import timedelta
from unittest.mock import patch

from app.jobs import worker
from app.jobs.worker import process_one, process_pending
from app.models import Job
from app.models.base import utcnow
from app.models.job import JOB_FAILED, JOB_QUEUED, JOB_RUNNING, JOB_SUCCEEDED
from app.repositories import jobs as jobs_repo
from app.services.claim_service import PermanentJobError, RetryableJobError


def _enqueue(db, job_type="test_job", **kw):
    job = jobs_repo.enqueue(db, job_type, **kw)
    db.commit()
    return job


def test_jobs_are_claimed_oldest_first_and_marked_running(db):
    first, second = _enqueue(db), _enqueue(db)
    first.created_at = utcnow() - timedelta(minutes=1)
    db.commit()
    claimed = jobs_repo.claim_next(db)
    assert claimed.id == first.id
    assert claimed.status == JOB_RUNNING and claimed.attempts == 1 and claimed.started_at
    assert jobs_repo.claim_next(db).id == second.id
    assert jobs_repo.claim_next(db) is None


def test_job_is_not_claimed_before_run_after(db):
    job = _enqueue(db)
    job.run_after = utcnow() + timedelta(minutes=5)
    db.commit()
    assert jobs_repo.claim_next(db) is None


def test_successful_job_stores_result(db):
    job = _enqueue(db)
    with patch.dict(worker.HANDLERS, {"test_job": lambda db_, j: {"ok": True}}):
        assert process_one() is True
    db.expire_all()
    done = db.get(Job, job.id)
    assert done.status == JOB_SUCCEEDED and done.result == {"ok": True} and done.finished_at


def test_retryable_error_requeues_with_exponential_backoff(db):
    job = _enqueue(db, max_attempts=3)

    def boom(db_, j):
        raise RetryableJobError("provider down")

    with patch.dict(worker.HANDLERS, {"test_job": boom}):
        process_one()
        db.expire_all()
        j = db.get(Job, job.id)
        assert j.status == JOB_QUEUED and j.attempts == 1
        first_delay = (j.run_after - utcnow().replace(tzinfo=j.run_after.tzinfo)).total_seconds()
        assert 0 < first_delay <= worker.BACKOFF_BASE_SECONDS

        j.run_after = utcnow()
        db.commit()
        process_one()
        db.expire_all()
        j = db.get(Job, job.id)
        second_delay = (j.run_after - utcnow().replace(tzinfo=j.run_after.tzinfo)).total_seconds()
        assert second_delay > first_delay                      # backoff grows (5s -> 10s)


def test_job_fails_permanently_after_max_attempts(db):
    job = _enqueue(db, max_attempts=2)

    def boom(db_, j):
        raise RetryableJobError("still down")

    with patch.dict(worker.HANDLERS, {"test_job": boom}):
        for _ in range(2):
            process_one()
            db.expire_all()
            j = db.get(Job, job.id)
            j.run_after = utcnow()
            db.commit()
    db.expire_all()
    j = db.get(Job, job.id)
    assert j.status == JOB_FAILED and j.attempts == 2 and "still down" in j.error


def test_permanent_error_does_not_retry(db):
    job = _enqueue(db, max_attempts=5)

    def boom(db_, j):
        raise PermanentJobError("bad input")

    with patch.dict(worker.HANDLERS, {"test_job": boom}):
        process_one()
    db.expire_all()
    j = db.get(Job, job.id)
    assert j.status == JOB_FAILED and j.attempts == 1


def test_unexpected_exception_is_contained_and_retried(db):
    job = _enqueue(db, max_attempts=3)

    def boom(db_, j):
        raise ZeroDivisionError("bug")

    with patch.dict(worker.HANDLERS, {"test_job": boom}):
        assert process_one() is True      # the worker loop survives handler bugs
    db.expire_all()
    j = db.get(Job, job.id)
    assert j.status == JOB_QUEUED and "ZeroDivisionError" in j.error


def test_unknown_job_type_fails_instead_of_looping(db):
    job = _enqueue(db, job_type="no_such_type", max_attempts=1)
    process_pending()
    db.expire_all()
    assert db.get(Job, job.id).status == JOB_FAILED


def test_stale_running_jobs_are_requeued(db):
    job = _enqueue(db)
    jobs_repo.claim_next(db)
    job.started_at = utcnow() - timedelta(minutes=30)     # worker died long ago
    db.commit()
    assert jobs_repo.requeue_stale(db) == 1
    db.expire_all()
    assert db.get(Job, job.id).status == JOB_QUEUED


def test_fresh_running_jobs_are_left_alone(db):
    _enqueue(db)
    jobs_repo.claim_next(db)
    assert jobs_repo.requeue_stale(db) == 0


def test_process_pending_drains_the_queue(db):
    for _ in range(4):
        _enqueue(db)
    with patch.dict(worker.HANDLERS, {"test_job": lambda db_, j: {}}):
        assert process_pending() == 4
        assert process_pending() == 0
