import os
from fastapi import APIRouter, UploadFile, File
from app.services.pdf_service import extract_text_from_pdf
from app.services.extraction_service import extract_claim_data
from app.services.classification_service import classify_denial
from app.services.risk_service import score_claim
from app.database import SessionLocal, Base, engine
from app.models import DenialClaim
from datetime import datetime

Base.metadata.create_all(bind=engine)

router = APIRouter()

UPLOAD_FOLDER = "app/uploads"


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # 1. Extract raw text
    extracted_text = extract_text_from_pdf(file_path)

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
    finally:
        db.close()

    return {
        "filename": file.filename,
        "structured_claim": structured_claim,
        "classification": classification,
        "risk_score": risk_result.get("risk_score"),
        "risk_level": risk_result.get("risk_level")
    }