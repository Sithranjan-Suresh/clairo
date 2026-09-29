import io
import os
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.upload import router as upload_router, UPLOAD_FOLDER

app = FastAPI()
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
