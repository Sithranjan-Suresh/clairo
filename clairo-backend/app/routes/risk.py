from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.limiter import limiter
from app.services.risk_service import score_claim

router = APIRouter()

MAX_QUEUE_SIZE = 25  # each claim triggers its own Groq call — cap batch cost


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
@limiter.limit("20/minute")
def score_single_claim(request: Request, payload: RiskScoreRequest):
    """
    Takes a single claim and returns a 0–100 risk score
    with rule flags and remediation recommendation.
    """
    result = score_claim(
        cpt_codes=payload.cpt_codes,
        payer=payload.payer,
        documentation_notes=payload.documentation_notes
    )
    return result


# ─────────────────────────────────────────
# CLAIM QUEUE ENDPOINT
# ─────────────────────────────────────────

@router.post("/score-queue")
@limiter.limit("5/minute")
def score_claim_queue(request: Request, payload: ClaimQueueRequest):
    """
    Takes a list of claims and returns risk scores for all of them.
    Sorted by risk_score descending so highest-risk claims surface first.
    """
    if len(payload.claims) > MAX_QUEUE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Too many claims in one request (max {MAX_QUEUE_SIZE}). "
            "Split into smaller batches.",
        )

    results = []

    for i, claim in enumerate(payload.claims):
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
