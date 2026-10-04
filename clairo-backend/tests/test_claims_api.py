"""Integration tests: HTTP -> auth -> services -> real DB, with only the LLM,
vector search and PDF text extraction mocked."""
import io
import os
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.config import UPLOAD_FOLDER
from app.jobs.worker import process_pending
from app.models import Appeal, AuditLog, DenialClaim, Document, Job, RiskScore

PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"

STRUCTURED = {
    "payer": "Aetna", "patient_id": "P-1001", "cpt_codes": ["29881"],
    "denial_reason": "Medical necessity not established",
    "billed_amount": "$4200", "denied_amount": "$4200", "service_date": "2026-05-10",
}
RISK = {
    "risk_score": 55, "risk_level": "MEDIUM", "rule_flags": ["PA required"],
    "remediation": "Add conservative-treatment notes.",
    "breakdown": {"rule_based_score": 25, "llm_documentation_score": 30},
}
APPEAL = {"appeal_letter": "Dear Aetna,\\nWe respectfully request...", "confidence_score": 82,
          "confidence_rationale": "Strong policy match."}
CITATIONS = [{"text": "Criteria...", "source": "Aetna Policy", "chunk_index": 1, "payer": "AETNA"}]


@pytest.fixture
def pipeline():
    """Mock every external dependency of the analysis/appeal pipeline."""
    with patch("app.services.claim_service.extract_text_from_pdf", return_value="denial text") as text, \
         patch("app.services.claim_service.extract_claim_data", return_value=dict(STRUCTURED)) as extract, \
         patch("app.services.claim_service.classify_denial", return_value="medical_necessity") as classify, \
         patch("app.services.claim_service.score_claim", return_value=RISK) as score, \
         patch("app.services.claim_service.retrieve_policy", return_value=CITATIONS) as retrieve, \
         patch("app.services.claim_service.generate_appeal", return_value=dict(APPEAL)) as appeal:
        yield {"text": text, "extract": extract, "classify": classify, "score": score,
               "retrieve": retrieve, "appeal": appeal}


def _upload(client, headers, name="denial.pdf", body=PDF_BYTES, ctype="application/pdf"):
    return client.post("/claims", headers=headers,
                       files={"file": (name, io.BytesIO(body), ctype)})


def _upload_and_process(client, headers, body=PDF_BYTES):
    res = _upload(client, headers, body=body)
    assert res.status_code == 202, res.text
    process_pending()
    return res.json()


# ---------------------------------------------------------------- upload validation
def test_upload_requires_authentication(client):
    res = client.post("/claims", files={"file": ("a.pdf", io.BytesIO(PDF_BYTES), "application/pdf")})
    assert res.status_code == 401


@pytest.mark.parametrize("name,ctype,body,status", [
    ("malware.exe", "application/octet-stream", PDF_BYTES, 400),
    ("notes.txt", "text/plain", b"hello", 400),
    ("fake.pdf", "image/png", PDF_BYTES, 400),               # lying extension
    ("empty.pdf", "application/pdf", b"", 400),
    ("renamed.pdf", "application/pdf", b"\x89PNG\r\n\x1a\n....", 422),   # not %PDF
    ("big.pdf", "application/pdf", b"%PDF" + b"0" * (16 * 1024 * 1024), 413),
], ids=["exe", "txt", "wrong-mime", "empty", "not-pdf-bytes", "oversized"])
def test_bad_uploads_are_rejected_cleanly(client, user, auth_headers, name, ctype, body, status):
    res = _upload(client, auth_headers(user), name=name, body=body, ctype=ctype)
    assert res.status_code == status
    assert "detail" in res.json()
    assert not os.path.isdir(UPLOAD_FOLDER) or not os.listdir(UPLOAD_FOLDER)  # nothing saved


def test_malicious_filename_never_reaches_the_filesystem(client, user, auth_headers, db, pipeline):
    res = _upload(client, auth_headers(user), name="../../../../etc/passwd.pdf")
    assert res.status_code == 202
    doc = db.scalars(select(Document)).one()
    assert doc.original_filename.endswith("passwd.pdf")        # kept only for display
    assert ".." not in doc.stored_filename and doc.stored_filename.endswith(".pdf")
    assert os.listdir(UPLOAD_FOLDER) == [doc.stored_filename]


# ---------------------------------------------------------------- the full workflow
def test_end_to_end_upload_analyze_appeal_audit(client, user, auth_headers, db, pipeline):
    headers = auth_headers(user)
    created = _upload_and_process(client, headers)

    job = client.get(f"/jobs/{created['job_id']}", headers=headers).json()
    assert job["status"] == "succeeded" and job["result"]["claim_id"] == created["claim_id"]

    claim = client.get(f"/claims/{created['claim_id']}", headers=headers).json()
    assert claim["status"] == "analyzed"
    assert claim["payer"] == "Aetna" and claim["cpt_codes"] == ["29881"]
    assert claim["classification"] == "medical_necessity"
    assert claim["risk_score"] == 55 and claim["risk_level"] == "MEDIUM"
    assert claim["is_demo"] is False
    assert claim["risk_history"][0]["flags"] == ["PA required"]
    assert claim["documents"][0]["original_filename"] == "denial.pdf"

    appeal_job = client.post(f"/claims/{claim['id']}/appeal", headers=headers)
    assert appeal_job.status_code == 202
    process_pending()
    claim = client.get(f"/claims/{claim['id']}", headers=headers).json()
    assert claim["status"] == "appealed" and claim["appeal_generated"] is True
    appeal = claim["appeals"][0]
    assert appeal["confidence_score"] == 82
    assert "\\n" not in appeal["letter_text"] and "\n" in appeal["letter_text"]
    assert appeal["citations"] == CITATIONS

    audit = client.get(f"/claims/{claim['id']}/audit", headers=headers).json()
    assert [a["action"] for a in audit] == [
        "claim.created", "claim.analyzed", "appeal.requested", "appeal.generated",
    ]
    assert all(a["request_id"] or a["action"].endswith(("analyzed", "generated")) for a in audit)


def test_claim_created_and_job_enqueued_atomically(client, user, auth_headers, db):
    """No pipeline mock and no worker run: the upload alone must have written the
    claim, document, job and audit row together."""
    res = _upload(client, auth_headers(user))
    assert res.status_code == 202
    assert db.scalar(select(DenialClaim).where(DenialClaim.id == res.json()["claim_id"])).status == "analyzing"
    assert db.scalars(select(Job)).one().status == "queued"
    assert db.scalars(select(AuditLog)).one().action == "claim.created"


# ---------------------------------------------------------------- caching + retries
def test_identical_pdf_skips_the_extraction_llm_call(client, user, auth_headers, pipeline):
    headers = auth_headers(user)
    first = _upload_and_process(client, headers)
    second = _upload_and_process(client, headers)
    assert first["claim_id"] != second["claim_id"]
    assert pipeline["extract"].call_count == 1          # second run served from cache
    analyzed = client.get(f"/claims/{second['claim_id']}/audit", headers=headers).json()
    assert analyzed[1]["details"]["extraction_cache_hit"] is True


def test_transient_llm_failure_is_retried_then_succeeds(client, user, auth_headers, db, pipeline):
    from app.repositories import jobs as jobs_repo
    pipeline["extract"].side_effect = [{"error": "LLM call failed"}, dict(STRUCTURED)]
    headers = auth_headers(user)
    created = _upload(client, headers).json()

    assert process_pending() == 1                        # attempt 1 fails -> requeued w/ backoff
    job = db.get(Job, created["job_id"])
    assert job.status == "queued" and job.attempts == 1 and "unavailable" in job.error
    job.run_after = job.created_at                       # fast-forward the backoff delay
    db.commit()
    assert process_pending() == 1
    db.expire_all()
    assert db.get(Job, created["job_id"]).status == "succeeded"
    assert db.get(DenialClaim, created["claim_id"]).status == "analyzed"
    assert jobs_repo.get(db, created["job_id"]).attempts == 2


def test_exhausted_retries_mark_claim_failed_and_reanalysis_recovers(client, user, auth_headers, db, pipeline):
    pipeline["extract"].return_value = {"error": "LLM call failed"}
    headers = auth_headers(user)
    created = _upload(client, headers).json()
    for _ in range(3):
        process_pending()
        db.expire_all()
        job = db.get(Job, created["job_id"])
        if job.status == "queued":
            job.run_after = job.created_at
            db.commit()
    claim = client.get(f"/claims/{created['claim_id']}", headers=headers).json()
    assert claim["status"] == "failed" and "unavailable" in claim["error_message"]
    assert db.get(Job, created["job_id"]).status == "failed"

    pipeline["extract"].return_value = dict(STRUCTURED)  # provider recovers
    assert client.post(f"/claims/{claim['id']}/analyze", headers=headers).status_code == 202
    process_pending()
    assert client.get(f"/claims/{claim['id']}", headers=headers).json()["status"] == "analyzed"


def test_unreadable_pdf_fails_fast_without_retrying(client, user, auth_headers, db):
    # Real PyMuPDF, real (broken) file: magic bytes pass upload validation but
    # the document can't be parsed.
    created = _upload(client, auth_headers(user), body=b"%PDF-1.4 this is not a real pdf").json()
    process_pending()
    job = db.get(Job, created["job_id"])
    assert job.status == "failed" and job.attempts == 1
    claim = db.get(DenialClaim, created["claim_id"])
    assert claim.status == "failed" and "PDF" in claim.error_message


def test_real_pdf_text_extraction_path(client, user, auth_headers, db):
    import fitz
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Denial letter: CPT 29881 not medically necessary")
    pdf = doc.tobytes()
    with patch("app.services.claim_service.extract_claim_data", return_value=dict(STRUCTURED)) as extract, \
         patch("app.services.claim_service.classify_denial", return_value="medical_necessity"), \
         patch("app.services.claim_service.score_claim", return_value=RISK):
        _upload_and_process(client, auth_headers(user), body=pdf)
    assert "CPT 29881" in extract.call_args.args[0]


# ---------------------------------------------------------------- authorization
def test_users_cannot_see_or_touch_each_others_claims(client, user, other_user, auth_headers, pipeline):
    created = _upload_and_process(client, auth_headers(user))
    cid = created["claim_id"]
    bob = auth_headers(other_user)
    assert client.get(f"/claims/{cid}", headers=bob).status_code == 404
    assert client.get(f"/claims/{cid}/audit", headers=bob).status_code == 404
    assert client.post(f"/claims/{cid}/appeal", headers=bob).status_code == 404
    assert client.get(f"/jobs/{created['job_id']}", headers=bob).status_code == 404
    assert client.get("/claims", headers=bob).json()["total"] == 0


def test_admin_sees_everything(client, user, admin, auth_headers, pipeline):
    created = _upload_and_process(client, auth_headers(user))
    assert client.get("/claims", headers=auth_headers(admin)).json()["total"] == 1
    assert client.get(f"/claims/{created['claim_id']}", headers=auth_headers(admin)).status_code == 200
    assert client.get(f"/jobs/{created['job_id']}", headers=auth_headers(admin)).status_code == 200


def test_demo_claims_are_readable_by_everyone_but_only_admins_can_modify(client, user, admin, auth_headers, db, pipeline):
    demo = DenialClaim(payer="UHC", cpt_codes="29881", classification="medical_necessity",
                       risk_score=80, status="analyzed", user_id=None, created_at="2026-01-01")
    db.add(demo)
    db.commit()
    headers = auth_headers(user)
    listing = client.get("/claims", headers=headers).json()
    assert listing["total"] == 1 and listing["items"][0]["is_demo"] is True
    assert client.get(f"/claims/{demo.id}", headers=headers).status_code == 200
    assert client.post(f"/claims/{demo.id}/appeal", headers=headers).status_code == 403
    assert client.post(f"/claims/{demo.id}/analyze", headers=headers).status_code == 403
    assert client.post(f"/claims/{demo.id}/appeal", headers=auth_headers(admin)).status_code == 202


def test_appeal_requires_an_analyzed_claim(client, user, auth_headers, pipeline):
    created = _upload(client, auth_headers(user)).json()      # not processed yet
    res = client.post(f"/claims/{created['claim_id']}/appeal", headers=auth_headers(user))
    assert res.status_code == 409


def test_unknown_claim_and_job_are_404(client, user, auth_headers):
    assert client.get("/claims/99999", headers=auth_headers(user)).status_code == 404
    assert client.get("/jobs/does-not-exist", headers=auth_headers(user)).status_code == 404


# ---------------------------------------------------------------- listing
@pytest.fixture
def seeded_claims(db, user):
    rows = [
        ("UHC", "29881", "medical_necessity", 85, "analyzed"),
        ("Aetna", "27447", "coding_mismatch", 45, "analyzed"),
        ("Cigna", "93306", "eligibility", 20, "appealed"),
        ("UHC", "70553", "prior_authorization", 72, "failed"),
        ("Aetna", "43239", "medical_necessity", None, "analyzing"),
    ]
    for payer, cpt, cls, score, status in rows:
        db.add(DenialClaim(payer=payer, cpt_codes=cpt, classification=cls, risk_score=score,
                           status=status, user_id=user.id, patient_id=f"P-{cpt}",
                           created_at="2026-02-01"))
    db.commit()


def _list(client, headers, **params):
    res = client.get("/claims", headers=headers, params=params)
    assert res.status_code == 200, res.text
    return res.json()


def test_list_pagination_is_stable_and_reports_total(client, user, auth_headers, seeded_claims):
    h = auth_headers(user)
    page1 = _list(client, h, limit=2, offset=0)
    page2 = _list(client, h, limit=2, offset=2)
    page3 = _list(client, h, limit=2, offset=4)
    assert page1["total"] == 5 and len(page1["items"]) == 2 and len(page3["items"]) == 1
    ids = [i["id"] for p in (page1, page2, page3) for i in p["items"]]
    assert len(set(ids)) == 5 and ids == sorted(ids, reverse=True)


def test_list_filters(client, user, auth_headers, seeded_claims):
    h = auth_headers(user)
    assert _list(client, h, payer="UHC")["total"] == 2
    assert _list(client, h, classification="medical_necessity")["total"] == 2
    assert _list(client, h, status="failed")["total"] == 1
    assert _list(client, h, risk="HIGH")["total"] == 2          # 85, 72
    assert _list(client, h, risk="medium")["total"] == 1        # 45
    assert _list(client, h, risk="LOW")["total"] == 1           # 20 (NULL score excluded)
    assert _list(client, h, q="27447")["total"] == 1
    assert _list(client, h, payer="UHC", risk="HIGH", status="analyzed")["total"] == 1


def test_list_sorting_always_puts_unscored_claims_last(client, user, auth_headers, seeded_claims):
    h = auth_headers(user)
    desc = [i["risk_score"] for i in _list(client, h, sort_by="risk_score", order="desc")["items"]]
    assert desc == [85, 72, 45, 20, None]
    asc = [i["risk_score"] for i in _list(client, h, sort_by="risk_score", order="asc")["items"]]
    assert asc == [20, 45, 72, 85, None]


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"sort_by": "password_hash"}, {"order": "sideways"},
])
def test_list_rejects_bad_query_params(client, user, auth_headers, params):
    assert client.get("/claims", headers=auth_headers(user), params=params).status_code == 422


def test_search_term_is_not_sql_injectable(client, user, auth_headers, seeded_claims):
    res = client.get("/claims", headers=auth_headers(user), params={"q": "'; DROP TABLE denial_claims;--"})
    assert res.status_code == 200 and res.json()["total"] == 0
    assert _list(client, auth_headers(user))["total"] == 5


def test_risk_history_is_kept_across_reanalysis(client, user, auth_headers, db, pipeline):
    h = auth_headers(user)
    created = _upload_and_process(client, h)
    client.post(f"/claims/{created['claim_id']}/analyze", headers=h)
    process_pending()
    assert len(db.scalars(select(RiskScore)).all()) == 2
    assert len(db.scalars(select(Appeal)).all()) == 0
