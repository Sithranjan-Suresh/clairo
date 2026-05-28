from fastapi import APIRouter
from pydantic import BaseModel
from app.services.risk_service import score_claim

router = APIRouter()


# ─────────────────────────────────────────
# INPUT SCHEMAS
# ─────────────────────────────────────────

class RiskScoreRequest(BaseModel):
    cpt_codes: list[str]
    payer: str
    documentation_notes: str


class ClaimQueueRequest(BaseModel):
    claims: list[RiskScoreRequest]


# ─────────────────────────────────────────
# SINGLE CLAIM ENDPOINT
# ─────────────────────────────────────────

@router.post("/score-claim")
def score_single_claim(request: RiskScoreRequest):
    """
    Takes a single claim and returns a 0–100 risk score
    with rule flags and remediation recommendation.
    """
    result = score_claim(
        cpt_codes=request.cpt_codes,
        payer=request.payer,
        documentation_notes=request.documentation_notes
    )
    return result


# ─────────────────────────────────────────
# CLAIM QUEUE ENDPOINT
# ─────────────────────────────────────────

@router.post("/score-queue")
def score_claim_queue(request: ClaimQueueRequest):
    """
    Takes a list of claims and returns risk scores for all of them.
    Sorted by risk_score descending so highest-risk claims surface first.
    """
    results = []

    for i, claim in enumerate(request.claims):
        result = score_claim(
            cpt_codes=claim.cpt_codes,
            payer=claim.payer,
            documentation_notes=claim.documentation_notes
        )
        result["claim_index"] = i
        result["cpt_codes"] = claim.cpt_codes
        result["payer"] = claim.payer
        results.append(result)

    results.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "total_claims": len(results),
        "high_risk_count": sum(1 for r in results if r["risk_level"] == "HIGH"),
        "medium_risk_count": sum(1 for r in results if r["risk_level"] == "MEDIUM"),
        "low_risk_count": sum(1 for r in results if r["risk_level"] == "LOW"),
        "results": results
    }