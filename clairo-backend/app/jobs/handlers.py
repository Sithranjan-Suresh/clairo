from app.models import Job
from app.services import claim_service

# job type -> callable(db, job) -> result dict
HANDLERS = {
    claim_service.JOB_ANALYZE: lambda db, job: claim_service.analyze_claim(db, job.claim_id),
    claim_service.JOB_APPEAL: lambda db, job: claim_service.generate_claim_appeal(
        db, job.claim_id, job.user_id
    ),
}

# Called once a job has exhausted its retries (or hit a permanent error), so the
# domain object can be moved to a terminal "failed" state the UI can show.
ON_FAILURE = {
    claim_service.JOB_ANALYZE: claim_service.on_analysis_failed,
}


def retryable_errors() -> tuple:
    return (claim_service.RetryableJobError,)


def permanent_errors() -> tuple:
    return (claim_service.PermanentJobError,)


__all__ = ["HANDLERS", "ON_FAILURE", "Job", "retryable_errors", "permanent_errors"]
