"""Background worker.

Runs either as a daemon thread inside the API process (default — keeps a
free single-service deployment working) or as its own process:

    python -m app.jobs.worker

Both claim jobs from the same Postgres table with SKIP LOCKED, so they can be
mixed freely.
"""
import logging
import threading
import time

from app.config import WORKER_POLL_SECONDS
from app.database import SessionLocal
from app.jobs.handlers import HANDLERS, ON_FAILURE, permanent_errors, retryable_errors
from app.observability import JOB_LATENCY, JOBS
from app.repositories import jobs as jobs_repo

logger = logging.getLogger(__name__)

BACKOFF_BASE_SECONDS = 5
STALE_SWEEP_EVERY = 60  # seconds


def _backoff(attempts: int) -> float:
    return BACKOFF_BASE_SECONDS * (2 ** max(attempts - 1, 0))   # 5s, 10s, 20s ...


def process_one(session_factory=SessionLocal) -> bool:
    """Claim and run a single job. Returns False when the queue is empty."""
    db = session_factory()
    try:
        job = jobs_repo.claim_next(db)
        if job is None:
            return False
        started = time.perf_counter()
        handler = HANDLERS.get(job.type)
        try:
            if handler is None:
                raise LookupError(f"no handler for job type {job.type!r}")
            result = handler(db, job)
        except retryable_errors() as exc:
            db.rollback()
            if job.attempts < job.max_attempts:
                delay = _backoff(job.attempts)
                logger.warning("job %s retry %d/%d in %ss: %s",
                               job.id, job.attempts, job.max_attempts, delay, exc)
                jobs_repo.mark_retry(db, job, str(exc), delay)
                JOBS.labels(job.type, "retry").inc()
            else:
                _fail(db, job, str(exc))
        except permanent_errors() as exc:
            db.rollback()
            _fail(db, job, str(exc))
        except Exception as exc:  # unexpected bug: treat like a transient error
            db.rollback()
            logger.exception("job %s crashed", job.id)
            if job.attempts < job.max_attempts:
                jobs_repo.mark_retry(db, job, f"internal error: {type(exc).__name__}",
                                     _backoff(job.attempts))
                JOBS.labels(job.type, "retry").inc()
            else:
                _fail(db, job, "Internal error while processing this job.")
        else:
            jobs_repo.mark_succeeded(db, job, result)
            JOBS.labels(job.type, "succeeded").inc()
        finally:
            JOB_LATENCY.labels(job.type).observe(time.perf_counter() - started)
        return True
    finally:
        db.close()


def _fail(db, job, error: str) -> None:
    hook = ON_FAILURE.get(job.type)
    if hook:
        try:
            hook(db, job, error)
        except Exception:
            db.rollback()
            logger.exception("on-failure hook for job %s failed", job.id)
    jobs_repo.mark_failed(db, job, error)
    JOBS.labels(job.type, "failed").inc()


def process_pending(max_jobs: int = 100, session_factory=SessionLocal) -> int:
    """Drain the queue synchronously (used by tests and one-off scripts)."""
    done = 0
    while done < max_jobs and process_one(session_factory):
        done += 1
    return done


class Worker(threading.Thread):
    def __init__(self) -> None:
        super().__init__(name="clairo-worker", daemon=True)
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        logger.info("worker started")
        last_sweep = 0.0
        while not self._stop_event.is_set():
            try:
                if time.monotonic() - last_sweep > STALE_SWEEP_EVERY:
                    db = SessionLocal()
                    try:
                        n = jobs_repo.requeue_stale(db)
                        if n:
                            logger.warning("requeued %d stale jobs", n)
                    finally:
                        db.close()
                    last_sweep = time.monotonic()
                if not process_one():
                    self._stop_event.wait(WORKER_POLL_SECONDS)
            except Exception:
                logger.exception("worker loop error")
                self._stop_event.wait(WORKER_POLL_SECONDS * 5)
        logger.info("worker stopped")


def main() -> None:
    from app.observability import configure_logging

    configure_logging()
    worker = Worker()
    worker.start()
    try:
        while worker.is_alive():
            worker.join(timeout=1)
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":
    main()
