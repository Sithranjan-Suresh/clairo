import logging
import os
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Optional

from fastapi import UploadFile

from app.services.pdf_service import extract_text_from_pdf

logger = logging.getLogger(__name__)

PREVIEW_CHARS = 1200
DOCX_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def clean_display_name(raw: str) -> str:
    """Convert file paths or snake_case filenames into readable labels."""
    if not raw:
        return "Uploaded Document"
    name = raw.replace("\\", "/").split("/")[-1]
    name = re.sub(r"\.(pdf|txt|docx|doc)$", "", name, flags=re.IGNORECASE)
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        return "Uploaded Document"
    return name.title()


def infer_document_type(filename: str) -> str:
    lower = filename.lower()
    checks = [
        (("denial", "eob", "remittance"), "Denial Letter / EOB"),
        (("clinical", "progress note", "hpi", "office visit", "supplemental"), "Clinical Notes"),
        (("prior authorization", "prior auth", "pa request"), "Prior Authorization Request"),
        (("imaging", "mri", "xray", "x-ray", "radiology", "ct "), "Imaging Report"),
        (("pt ", "physical therapy", "therapy note"), "PT Notes"),
        (("referral", "order", "prescription"), "Referral / Order"),
        (("operative", "op report", "surgery"), "Operative Report"),
    ]
    for keywords, label in checks:
        if any(k in lower for k in keywords):
            return label
    return "Supporting Documentation"


def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def extract_text_from_docx(file_path: str) -> str:
    with zipfile.ZipFile(file_path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    parts = []
    for node in root.iter(f"{DOCX_NS}t"):
        if node.text:
            parts.append(node.text)
    return " ".join(parts)


def extract_document_text(
    file_path: str,
    filename: str,
    content_type: str = "",
) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if not ext and content_type:
        lowered = content_type.lower()
        if "pdf" in lowered:
            ext = ".pdf"
        elif "text" in lowered or "plain" in lowered:
            ext = ".txt"
        elif "wordprocessingml" in lowered or "msword" in lowered:
            ext = ".docx"

    if ext == ".pdf":
        try:
            return extract_text_from_pdf(file_path)
        except Exception as pdf_error:
            try:
                text = extract_text_from_txt(file_path)
                if text.strip():
                    logger.warning(
                        "Prior auth PDF extraction failed for %s; used plain-text fallback",
                        filename,
                    )
                    return text
            except Exception:
                pass
            raise pdf_error
    if ext == ".txt":
        return extract_text_from_txt(file_path)
    if ext in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    raise ValueError(f"Unsupported file type: {ext or 'unknown'}")


async def process_uploaded_documents(files: List[UploadFile]) -> tuple[List[dict], List[str]]:
    """
    Process uploaded files into structured document records.
    Returns (documents, warnings).
    """
    documents: List[dict] = []
    warnings: List[str] = []

    if not files:
        return documents, warnings

    for upload in files:
        filename = upload.filename or "document.pdf"
        suffix = os.path.splitext(filename)[1] or ".pdf"

        try:
            content = await upload.read()
            if not content:
                warnings.append(f"{filename}: file was empty.")
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                text = extract_document_text(
                    tmp_path,
                    filename,
                    upload.content_type or "",
                )
                preview = (text or "").strip()[:PREVIEW_CHARS]
                if not preview:
                    warnings.append(f"{filename}: no readable text extracted.")
                    preview = "[No readable text found in document]"

                documents.append(
                    {
                        "filename": filename,
                        "display_name": clean_display_name(filename),
                        "document_type": infer_document_type(filename),
                        "text_preview": preview,
                        "full_text": (text or "").strip(),
                    }
                )
                logger.info(
                    "Prior auth document extracted: %s (%d chars)",
                    filename,
                    len((text or "").strip()),
                )
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as exc:
            logger.exception("Prior auth extraction failed for %s", filename)
            warnings.append(f"{filename}: extraction failed — {exc}")

    return documents, warnings


def build_documents_context(documents: List[dict]) -> str:
    blocks = []
    for doc in documents:
        blocks.append(
            f"DOCUMENT: {doc['display_name']}\n"
            f"TYPE: {doc['document_type']}\n"
            f"CONTENT:\n{doc['full_text'][:8000]}"
        )
    return "\n\n---\n\n".join(blocks)


def build_policy_context(retrieved: List[dict]) -> tuple[str, str]:
    if not retrieved:
        return "", "No payer policy evidence retrieved"

    blocks = []
    for item in retrieved:
        source = clean_display_name(item.get("source", "Payer Policy"))
        chunk = item.get("chunk_index", "")
        text = item.get("text", "")
        blocks.append(
            f"SOURCE: {source}\nSECTION: Chunk {chunk}\n\nCONTENT:\n{text}"
        )

    primary = clean_display_name(retrieved[0].get("source", "Payer Policy"))
    return "\n\n".join(blocks), primary


def parse_cpt_codes(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [code.strip() for code in re.split(r"[,\s]+", raw) if code.strip()]


def parse_diagnosis_codes(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [code.strip() for code in re.split(r"[,\s]+", raw) if code.strip()]


def fallback_pa_packet(
    payer: str,
    cpt_codes: List[str],
    warnings: Optional[List[str]] = None,
    raw: Optional[str] = None,
    groq_error: Optional[str] = None,
) -> dict:
    warning_note = ""
    if warnings:
        warning_note = " Processing warnings: " + "; ".join(warnings)
    if groq_error:
        warning_note += f" Groq error: {groq_error}"
    if raw:
        warning_note += " Model output could not be parsed."

    return {
        "pa_required": "unknown",
        "confidence": 0,
        "requested_service_summary": f"Prior authorization review for {payer} — CPT {', '.join(cpt_codes) or 'N/A'}.",
        "medical_necessity_summary": "Unable to generate a structured summary. Please review uploaded documents manually.",
        "policy_requirements": [],
        "documentation_present": [],
        "documentation_missing": [
            {
                "missing_item": "Structured AI review unavailable",
                "why_needed": "The model response could not be parsed into a checklist.",
                "recommended_action": "Retry generation or review documents manually.",
            }
        ],
        "clinical_evidence_by_document": [],
        "provider_ready_summary": "Prior authorization packet could not be fully generated." + warning_note,
        "recommended_next_steps": [
            "Verify uploaded documents contain legible clinical text.",
            "Retry packet generation.",
            "Review payer policy requirements manually.",
        ],
        "doctor_review_notes": warning_note.strip() or "Manual review recommended.",
    }
