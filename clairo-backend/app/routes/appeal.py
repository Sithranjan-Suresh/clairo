from fastapi import APIRouter, Request
from app.limiter import limiter
from app.services.appeal_service import generate_appeal
from app.rag.retriever import retrieve_policy
from pydantic import BaseModel

router = APIRouter()


@router.post("/generate-appeal")
@limiter.limit("10/minute")
def generate(request: Request):

    structured_claim = {
        "payer": "UHC",
        "patient_id": "P12345",
        "cpt_codes": ["29881"],
        "denial_reason": "Medical necessity was not established — documentation did not show two failed conservative treatments prior to surgery.",
        "billed_amount": "$4200",
        "denied_amount": "$4200",
        "service_date": "2026-05-10"
    }

    classification = "medical_necessity"

    retrieved = retrieve_policy(
        payer="UHC",
        query="",
        top_k=3,
        classification=classification,
        cpt="29881",
        denial_reason="Medical necessity was not established — documentation did not show two failed conservative treatments prior to surgery."
    )

    result = generate_appeal(
        structured_claim=structured_claim,
        classification=classification,
        retrieved_policies=retrieved
    )

    return result




class AppealRequest(BaseModel):
    structured_claim: dict
    classification: str


@router.post("/generate-from-claim")
@limiter.limit("10/minute")
def generate_from_claim(request: Request, payload: AppealRequest):

    cpt_codes = payload.structured_claim.get("cpt_codes", [])
    cpt = cpt_codes[0] if cpt_codes else ""
    denial_reason = payload.structured_claim.get("denial_reason", "")
    payer = payload.structured_claim.get("payer", "")

    retrieved = retrieve_policy(
        payer=payer,
        query="",
        top_k=3,
        classification=payload.classification,
        cpt=cpt,
        denial_reason=denial_reason
    )

    result = generate_appeal(
        structured_claim=payload.structured_claim,
        classification=payload.classification,
        retrieved_policies=retrieved
    )

    return result
