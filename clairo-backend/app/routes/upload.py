import logging
import os
import uuid
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from app.services.pdf_service import extract_text_from_pdf

from app.limiter import limiter
from app.services.extraction_service import extract_claim_data
from app.services.classification_service import classify_denial
from app.services.risk_service import score_claim
from app.database import SessionLocal, Base, engine
from app.models import DenialClaim
from datetime import datetime

Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_FOLDER = "app/uploads"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_pdf(request: Request, file: UploadFile = File(...)):

    if not (file.filename or "").lower().endswith(".pdf") or file.content_type not in (
        "application/pdf",
        "application/x-pdf",
    ):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Never trust the client-supplied filename for the on-disk path (path
    # traversal risk, e.g. "../../etc/passwd") — generate our own name and
    # keep the original only for display purposes.
    safe_name = f"{uuid.uuid4().hex}.pdf"
    file_path = os.path.join(UPLOAD_FOLDER, safe_name)

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 15 MB).")

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # 1. Extract raw text — PyMuPDF raises on a corrupted/non-PDF byte
    # stream (e.g. a renamed .txt/.png passed off as .pdf despite the
    # content-type check above), and this was previously uncaught,
    # producing a bare 500 with no CORS headers instead of a clean error.
    try:
        extracted_text = extract_text_from_pdf(file_path)
    except Exception as exc:
        logger.warning("PDF text extraction failed for %s: %s", safe_name, exc)
        os.remove(file_path)
        raise HTTPException(
            status_code=422,
            detail="Could not read this file as a PDF. It may be corrupted, "
            "password-protected, or not a valid PDF.",
        ) from exc

    # 2. Structured claim extraction
    structured_claim = extract_claim_data(extracted_text)

    # 3. Denial classification
    classification = classify_denial(structured_claim)

    # 4. Risk score
    cpt_codes = structured_claim.get("cpt_codes", [])
    payer = structured_claim.get("payer", "Unknown")
    risk_result = score_claim(
        cpt_codes=cpt_codes,
        payer=payer,
        documentation_notes=structured_claim.get("denial_reason", "")
    )

    # 5. Save to database
    db = SessionLocal()
    try:
        claim_record = DenialClaim(
            payer=payer,
            patient_id=structured_claim.get("patient_id"),
            cpt_codes=", ".join(cpt_codes) if cpt_codes else None,
            denial_reason=structured_claim.get("denial_reason"),
            classification=classification,
            billed_amount=structured_claim.get("billed_amount"),
            denied_amount=structured_claim.get("denied_amount"),
            service_date=structured_claim.get("service_date"),
            risk_score=risk_result.get("risk_score"),
            appeal_generated=0,
            created_at=datetime.now().strftime("%Y-%m-%d")
        )
        db.add(claim_record)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {
        "filename": file.filename or safe_name,
        "structured_claim": structured_claim,
        "classification": classification,
        "risk_score": risk_result.get("risk_score"),
        "risk_level": risk_result.get("risk_level")
    }