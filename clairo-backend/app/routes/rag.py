from fastapi import APIRouter
from app.rag.retriever import retrieve_policy

router = APIRouter()


@router.get("/retrieve")
def retrieve(payer: str, cpt: str, denial_reason: str, classification: str = ""):
    results = retrieve_policy(
        payer=payer,
        query="",
        top_k=3,
        classification=classification,
        cpt=cpt,
        denial_reason=denial_reason
    )

    return {
        "payer": payer,
        "cpt": cpt,
        "denial_reason": denial_reason,
        "results": results
    }