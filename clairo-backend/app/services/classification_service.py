import logging
import re

from app.services.groq_services import CHAT_MODEL, client

logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = {
    "medical_necessity",
    "prior_authorization",
    "coding_mismatch",
    "eligibility",
    "documentation_gap",
    "timely_filing",
}

DEFAULT_CATEGORY = "documentation_gap"


def classify_denial(structured_claim: dict) -> str:
    """Classify a denial into one of ALLOWED_CATEGORIES. Always returns a
    value from that set — never raw, unvalidated LLM output — since
    downstream logic (e.g. appeal viability scoring) matches on it exactly."""

    prompt = f"""
You are a medical insurance denial classification engine.

Classify the claim into EXACTLY ONE category.

Allowed categories:
- medical_necessity
- prior_authorization
- coding_mismatch
- eligibility
- documentation_gap
- timely_filing

RULES:
- Output ONLY the category name
- No explanation
- No extra text
- No punctuation

CLAIM:
{structured_claim}
"""

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        raw = response.choices[0].message.content.strip()
    except Exception:
        logger.exception("classify_denial: Groq call failed, using default category")
        return DEFAULT_CATEGORY

    normalized = re.sub(r"[^a-z_]", "", raw.strip().lower())
    if normalized in ALLOWED_CATEGORIES:
        return normalized

    logger.warning("classify_denial: unrecognized category %r, using default", raw)
    return DEFAULT_CATEGORY