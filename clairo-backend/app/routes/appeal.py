from fastapi import APIRouter
from app.services.appeal_service import generate_appeal
from app.rag.retriever import retrieve_policy
from pydantic import BaseModel

router = APIRouter()


@router.post("/generate-appeal")
def generate():

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
def generate_from_claim(request: AppealRequest):

    cpt_codes = request.structured_claim.get("cpt_codes", [])
    cpt = cpt_codes[0] if cpt_codes else ""
    denial_reason = request.structured_claim.get("denial_reason", "")
    payer = request.structured_claim.get("payer", "")

    retrieved = retrieve_policy(
        payer=payer,
        query="",
        top_k=3,
        classification=request.classification,
        cpt=cpt,
        denial_reason=denial_reason
    )

    result = generate_appeal(
        structured_claim=request.structured_claim,
        classification=request.classification,
        retrieved_policies=retrieved
    )

    return result