import io
import os
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.limiter import limiter
from app.routes.upload import router as upload_router, UPLOAD_FOLDER

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(status_code=429, content={"error": "rate limited"}),
)
app.add_middleware(SlowAPIMiddleware)
app.include_router(upload_router)
client = TestClient(app)

_PATCHES = dict(
    extract_text_from_pdf=("app.routes.upload.extract_text_from_pdf", "denial text"),
    extract_claim_data=(
        "app.routes.upload.extract_claim_data",
        {
            "payer": "Aetna",
            "patient_id": "P1",
            "cpt_codes": ["29881"],
            "denial_reason": "not medically necessary",
            "billed_amount": "$100",
            "denied_amount": "$100",
            "service_date": "2026-01-01",
        },
    ),
    classify_denial=("app.routes.upload.classify_denial", "medical_necessity"),
    score_claim=(
        "app.routes.upload.score_claim",
        {"risk_score": 42, "risk_level": "MEDIUM"},
    ),
)


def _upload(filename: str, content_type: str = "application/pdf", body: bytes = b"%PDF-1.4 fake"):
    with patch(_PATCHES["extract_text_from_pdf"][0], return_value=_PATCHES["extract_text_from_pdf"][1]), \
         patch(_PATCHES["extract_claim_data"][0], return_value=_PATCHES["extract_claim_data"][1]), \
         patch(_PATCHES["classify_denial"][0], return_value=_PATCHES["classify_denial"][1]), \
         patch(_PATCHES["score_claim"][0], return_value=_PATCHES["score_claim"][1]):
        return client.post(
            "/upload",
            files={"file": (filename, io.BytesIO(body), content_type)},
        )


def test_malicious_filename_never_escapes_upload_folder():
    before = set(os.listdir(UPLOAD_FOLDER)) if os.path.isdir(UPLOAD_FOLDER) else set()

    response = _upload("../../../../etc/passwd.pdf")

    assert response.status_code == 200
    after = set(os.listdir(UPLOAD_FOLDER))
    new_files = after - before
    assert len(new_files) == 1
    # The server-generated name is a uuid hex + .pdf, never the raw client filename.
    saved_name = new_files.pop()
    assert saved_name != "../../../../etc/passwd.pdf"
    assert saved_name != "passwd.pdf"
    assert saved_name.endswith(".pdf")

    os.remove(os.path.join(UPLOAD_FOLDER, saved_name))


def test_non_pdf_upload_is_rejected():
    response = _upload("malware.exe", content_type="application/octet-stream")
    assert response.status_code == 400


def test_oversized_upload_is_rejected():
    response = _upload("big.pdf", body=b"0" * (16 * 1024 * 1024))
    assert response.status_code == 413


def test_corrupted_pdf_returns_clean_error_not_bare_500():
    """A file that passes the content-type check but PyMuPDF can't
    actually parse (corrupted, password-protected, or just not real PDF
    bytes) used to raise unhandled all the way out of the route, producing
    a bare 500 with no JSON body and no CORS headers — confirmed live on
    the deployed backend. It should now be a clean 422 with a JSON detail."""
    before = set(os.listdir(UPLOAD_FOLDER)) if os.path.isdir(UPLOAD_FOLDER) else set()

    with patch(
        _PATCHES["extract_text_from_pdf"][0],
        side_effect=RuntimeError("cannot open broken document"),
    ):
        response = client.post(
            "/upload",
            files={"file": ("broken.pdf", io.BytesIO(b"%PDF-1.4 not really"), "application/pdf")},
        )

    assert response.status_code == 422
    assert "detail" in response.json()

    # The saved-then-unreadable file should be cleaned up, not left behind.
    after = set(os.listdir(UPLOAD_FOLDER)) if os.path.isdir(UPLOAD_FOLDER) else set()
    assert after == before
