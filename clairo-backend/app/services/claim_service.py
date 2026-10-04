"""Claim lifecycle: upload -> analyze (extract, classify, score) -> appeal.

Routes stay thin; the transactional work lives here. analyze/appeal are run by
background workers (see app/jobs), never inline in a request.
"""
import hashlib
import logging
import os
import uuid
from typing import Optional

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.cache import cache
from app.config import CACHE_TTL_ANALYSIS, JOB_MAX_ATTEMPTS, MAX_UPLOAD_BYTES, UPLOAD_FOLDER
from app.models import DenialClaim, Job, User
from app.models.claim import STATUS_ANALYZED, STATUS_ANALYZING, STATUS_APPEALED, STATUS_FAILED
from app.rag.retriever import retrieve_policy
from app.repositories import claims as claims_repo
from app.repositories import jobs as jobs_repo
from app.services import audit_service
from app.services.appeal_service import generate_appeal
from app.services.classification_service import classify_denial
from app.services.extraction_service import extract_claim_data
from app.services.groq_services import CHAT_MODEL
from app.services.pdf_service import extract_text_from_pdf
from app.services.risk_service import score_claim

logger = logging.getLogger(__name__)

JOB_ANALYZE = "analyze_claim"
JOB_APPEAL = "generate_appeal"


class RetryableJobError(Exception):
    """Transient failure (e.g. LLM provider hiccup) — the queue retries with backoff."""


class PermanentJobError(Exception):
    """Won't succeed on retry (e.g. unreadable PDF) — fail the job immediately."""


# --------------------------------------------------------------------------- upload
def validate_upload(filename: Optional[str], content_type: Optional[str], content: bytes) -> None:
    if not (filename or "").lower().endswith(".pdf") or content_type not in (
        "application/pdf", "application/x-pdf",
    ):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 15 MB).")
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if not content.lstrip().startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail="This file doesn't look like a valid PDF.")


def create_claim_from_upload(
    db: Session, user: User, *, filename: Optional[str], content_type: Optional[str],
    content: bytes, request: Optional[Request] = None,
):
    """File + claim + document + queued analysis job in ONE transaction."""
    validate_upload(filename, content_type, content)

    # Never trust the client filename for the on-disk path (path traversal).
    stored_name = f"{uuid.uuid4().hex}.pdf"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    path = os.path.join(UPLOAD_FOLDER, stored_name)
    with open(path, "wb") as fh:
        fh.write(content)

    try:
        claim = claims_repo.create(db, user_id=user.id, status=STATUS_ANALYZING)
        claims_repo.add_document(
            db, claim_id=claim.id, user_id=user.id,
            original_filename=(filename or stored_name)[:255], stored_filename=stored_name,
            content_type=content_type, size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )
        job = jobs_repo.enqueue(db, JOB_ANALYZE, claim_id=claim.id, user_id=user.id,
                                max_attempts=JOB_MAX_ATTEMPTS)
        audit_service.record(
            db, "claim.created", user=user, entity_type="claim", entity_id=claim.id,
            details={"filename": filename, "size_bytes": len(content), "job_id": job.id},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        os.path.exists(path) and os.remove(path)   # don't orphan the file
        raise
    return claim, job


def enqueue_analysis(db: Session, claim: DenialClaim, user: User, request: Optional[Request] = None) -> Job:
    claim.status = STATUS_ANALYZING
    claim.error_message = None
    job = jobs_repo.enqueue(db, JOB_ANALYZE, claim_id=claim.id, user_id=user.id,
                            max_attempts=JOB_MAX_ATTEMPTS)
    audit_service.record(db, "claim.reanalysis_requested", user=user, entity_type="claim",
                         entity_id=claim.id, details={"job_id": job.id}, request=request)
    db.commit()
    return job


def enqueue_appeal(db: Session, claim: DenialClaim, user: User, request: Optional[Request] = None) -> Job:
    job = jobs_repo.enqueue(db, JOB_APPEAL, claim_id=claim.id, user_id=user.id,
                            max_attempts=JOB_MAX_ATTEMPTS)
    audit_service.record(db, "appeal.requested", user=user, entity_type="claim",
                         entity_id=claim.id, details={"job_id": job.id}, request=request)
    db.commit()
    return job


# ---------------------------------------------------------------------- job handlers
def _structured_from_claim(claim: DenialClaim) -> dict:
    return {
        "payer": claim.payer,
        "patient_id": claim.patient_id,
        "cpt_codes": claim.cpt_list,
        "denial_reason": claim.denial_reason,
        "billed_amount": claim.billed_amount,
        "denied_amount": claim.denied_amount,
        "service_date": claim.service_date,
    }


def analyze_claim(db: Session, claim_id: int) -> dict:
    claim = db.get(DenialClaim, claim_id)
    if claim is None:
        raise PermanentJobError("Claim no longer exists.")
    if not claim.documents:
        raise PermanentJobError("Claim has no uploaded document.")
    doc = claim.documents[0]

    # Identical PDFs (re-uploads, retries, demo runs) skip the extraction LLM call.
    structured = cache.get("analysis", doc.sha256)
    cache_hit = structured is not None
    if not cache_hit:
        try:
            text = extract_text_from_pdf(os.path.join(UPLOAD_FOLDER, doc.stored_filename))
        except Exception as exc:
            raise PermanentJobError(
                "Could not read this file as a PDF. It may be corrupted or password-protected."
            ) from exc
        if not text.strip():
            raise PermanentJobError(
                "No readable text found. Scanned/image-only PDFs aren't supported yet."
            )
        structured = extract_claim_data(text)
        if structured.get("error"):
            raise RetryableJobError("AI extraction is temporarily unavailable.")
        cache.set("analysis", doc.sha256, structured, CACHE_TTL_ANALYSIS)

    cpt_codes = [str(c) for c in (structured.get("cpt_codes") or [])]
    payer = structured.get("payer") or "Unknown"
    classification = classify_denial(structured)
    risk = score_claim(
        cpt_codes=cpt_codes, payer=payer,
        documentation_notes=structured.get("denial_reason") or "",
    )

    claim.payer = payer
    claim.patient_id = structured.get("patient_id")
    claim.cpt_codes = ", ".join(cpt_codes) if cpt_codes else None
    claim.denial_reason = structured.get("denial_reason")
    claim.billed_amount = structured.get("billed_amount")
    claim.denied_amount = structured.get("denied_amount")
    claim.service_date = structured.get("service_date")
    claim.classification = classification
    claim.risk_score = risk["risk_score"]
    claim.status = STATUS_ANALYZED
    claim.error_message = None
    claims_repo.add_risk_score(
        db, claim_id=claim.id, score=risk["risk_score"], level=risk["risk_level"],
        rule_score=risk["breakdown"]["rule_based_score"],
        llm_score=risk["breakdown"]["llm_documentation_score"],
        flags=risk["rule_flags"], remediation=risk["remediation"],
    )
    audit_service.record(
        db, "claim.analyzed", user=claim.owner, entity_type="claim", entity_id=claim.id,
        details={"risk_score": risk["risk_score"], "classification": classification,
                 "extraction_cache_hit": cache_hit},
    )
    db.commit()
    return {"claim_id": claim.id, "risk_score": risk["risk_score"], "cache_hit": cache_hit}


def on_analysis_failed(db: Session, job: Job, error: str) -> None:
    claim = db.get(DenialClaim, job.claim_id) if job.claim_id else None
    if claim is None:
        return
    claim.status = STATUS_FAILED
    claim.error_message = error[:500]
    audit_service.record(db, "claim.analysis_failed", user=claim.owner, entity_type="claim",
                         entity_id=claim.id, details={"error": error[:500], "job_id": job.id})
    db.commit()


def generate_claim_appeal(db: Session, claim_id: int, user_id: Optional[int]) -> dict:
    claim = db.get(DenialClaim, claim_id)
    if claim is None:
        raise PermanentJobError("Claim no longer exists.")
    if not claim.classification or not claim.payer:
        raise PermanentJobError("Claim hasn't been analyzed yet.")
    structured = _structured_from_claim(claim)
    cpts = claim.cpt_list
    try:
        retrieved = retrieve_policy(
            payer=claim.payer, query="", top_k=3, classification=claim.classification,
            cpt=cpts[0] if cpts else "", denial_reason=claim.denial_reason or "",
        )
    except Exception:
        logger.exception("policy retrieval failed; drafting appeal without citations")
        retrieved = []

    result = generate_appeal(structured, claim.classification, retrieved)
    if result.get("generation_failed"):
        raise RetryableJobError("AI appeal generation is temporarily unavailable.")

    appeal = claims_repo.add_appeal(
        db, claim_id=claim.id, user_id=user_id,
        letter_text=(result.get("appeal_letter") or "").replace("\\n", "\n"),
        confidence_score=int(result.get("confidence_score") or 0),
        confidence_rationale=result.get("confidence_rationale"),
        citations=retrieved, model=CHAT_MODEL,
    )
    claim.appeal_generated = 1
    claim.status = STATUS_APPEALED
    audit_service.record(
        db, "appeal.generated", user=claim.owner, entity_type="claim", entity_id=claim.id,
        details={"appeal_id": appeal.id, "confidence": appeal.confidence_score,
                 "citations": len(retrieved)},
    )
    db.commit()
    return {"claim_id": claim.id, "appeal_id": appeal.id}


def to_summary(claim: DenialClaim) -> dict:
    return {
        "id": claim.id, "payer": claim.payer, "patient_id": claim.patient_id,
        "cpt_codes": claim.cpt_list, "classification": claim.classification,
        "risk_score": claim.risk_score, "risk_level": claims_repo.risk_level(claim.risk_score),
        "status": claim.status or STATUS_ANALYZED,
        "appeal_generated": bool(claim.appeal_generated),
        "billed_amount": claim.billed_amount, "denied_amount": claim.denied_amount,
        "service_date": claim.service_date, "created_at": claim.created_at,
        "is_demo": claim.user_id is None,
    }


def to_detail(claim: DenialClaim) -> dict:
    data = to_summary(claim)
    data.update({
        "denial_reason": claim.denial_reason, "error_message": claim.error_message,
        "owner_id": claim.user_id,
        "documents": claim.documents, "risk_history": claim.risk_scores,
        "appeals": claim.appeals,
    })
    return data
