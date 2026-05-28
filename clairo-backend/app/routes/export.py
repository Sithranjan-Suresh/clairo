from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import io

from app.services.pdf_export_service import generate_appeal_pdf
from app.services.appeal_service import generate_appeal, get_appeal_viability
from app.rag.retriever import retrieve_policy

router = APIRouter()


class ExportRequest(BaseModel):
    appeal_letter: str
    structured_claim: dict
    confidence_score: int
    classification: str


class ViabilityRequest(BaseModel):
    confidence_score: int
    classification: str
    payer: str


@router.post("/export-pdf")
def export_appeal_pdf(request: ExportRequest):
    pdf_bytes = generate_appeal_pdf(
        appeal_letter=request.appeal_letter,
        claim=request.structured_claim
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=appeal_letter.pdf"}
    )


@router.post("/viability")
def appeal_viability(request: ViabilityRequest):
    result = get_appeal_viability(
        confidence_score=request.confidence_score,
        classification=request.classification,
        payer=request.payer
    )
    return result