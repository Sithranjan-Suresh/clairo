import re  # CHANGED: added
from app.rag.vectorstore import collection
from app.rag.embedder import get_embedding


# CHANGED: expanded alias table — handles case, spacing, punctuation variants
PAYER_ALIASES = {
    "uhc": "uhc",
    "unitedhealthcare": "uhc",
    "unitedhealth": "uhc",
    "united health": "uhc",
    "united healthcare": "uhc",
    "united health care": "uhc",
    "united": "uhc",
    "uhg": "uhc",
    "aetna": "aetna",
    "cvs aetna": "aetna",
    "cvs health": "aetna",
    "bcbs": "bcbs",
    "bluecross": "bcbs",
    "blue cross": "bcbs",
    "blue cross blue shield": "bcbs",
    "anthem": "bcbs",
    "elevance": "bcbs",
    "cigna": "cigna",
    "cigna healthspring": "cigna",
    "evernorth": "cigna",
    "humana": "humana",
    "medicare": "medicare",
    "chpw": "chpw",
    "community health plan": "chpw",
    "centene": "centene",
    "health net": "centene",
    "molina": "molina",
    "molina healthcare": "molina",
    "kaiser": "kaiser",
    "kaiser permanente": "kaiser",
    "excellus": "excellus_bcbs",
    "excellus bcbs": "excellus_bcbs",
    "excellus bluecross": "excellus_bcbs",
    "arkansas bcbs": "arkansas_bcbs",
    "arkansas blue cross": "arkansas_bcbs",
}

DENIAL_QUERY_TEMPLATES = {
    "medical_necessity": (
        "medical necessity criteria clinical indications coverage requirements "
        "proven medically necessary failed conservative treatment documentation required"
    ),
    "prior_authorization": (
        "prior authorization requirements precertification approval criteria "
        "authorization required before service"
    ),
    "coding_mismatch": (
        "CPT code billing guidelines bundling rules modifier requirements "
        "separate billing reimbursement policy"
    ),
    "documentation_gap": (
        "documentation requirements clinical records physician notes "
        "supporting documentation required for coverage"
    ),
    "eligibility": (
        "eligibility coverage criteria benefit plan member coverage "
        "coordination of benefits"
    ),
    "timely_filing": (
        "timely filing deadline claim submission requirements appeal deadline"
    ),
}


# CHANGED: strips punctuation before alias lookup so "UnitedHealthCare" == "unitedhealthcare"
def normalize_payer(payer: str) -> str:
    key = payer.lower().strip()
    key = re.sub(r"[^a-z0-9 ]", "", key).strip()
    return PAYER_ALIASES.get(key, key)


def build_enriched_query(payer: str, cpt: str, denial_reason: str, classification: str = None) -> str:
    base = f"CPT code {cpt} {payer} coverage policy medical necessity criteria clinical indications"

    if classification and classification in DENIAL_QUERY_TEMPLATES:
        base += " " + DENIAL_QUERY_TEMPLATES[classification]
    else:
        base += f" {denial_reason} documentation requirements coverage criteria indications"

    return base


def score_chunk_relevance(chunk_text: str, cpt: str, denial_reason: str) -> int:
    score = 0
    text_lower = chunk_text.lower()
    cpt_lower = cpt.lower()
    denial_lower = denial_reason.lower()

    if cpt_lower in text_lower:
        score += 3
    if "medical necessity" in text_lower or "medically necessary" in text_lower:
        score += 3
    if "criteria" in text_lower or "indication" in text_lower:
        score += 2
    if "proven" in text_lower or "not medically necessary" in text_lower or "covered" in text_lower:
        score += 2

    for keyword in denial_lower.split():
        if len(keyword) > 4 and keyword in text_lower:
            score += 1

    boilerplate_signals = [
        "reserves the right to modify",
        "informational purposes",
        "does not constitute medical advice",
        "member specific benefit plan",
        "business associate",
        "in the event of a conflict"
    ]
    for signal in boilerplate_signals:
        if signal in text_lower:
            score -= 3

    return score

# CHANGED: converts raw ingestion paths like "app/data/policies/aetna_medical_necessity.pdf"
# into a human-readable label like "Aetna Medical Necessity" for display in the UI.
def clean_source_label(source: str) -> str:
    if not source:
        return "Unknown Policy"
    name = source.replace("\\", "/").split("/")[-1]
    name = re.sub(r"\.(pdf|txt|docx|doc)$", "", name, flags=re.IGNORECASE)
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name.title() if name else "Unknown Policy"

def retrieve_policy(payer: str, query: str, top_k: int = 3, classification: str = None, cpt: str = "", denial_reason: str = "") -> list:

    normalized_payer = normalize_payer(payer)

    if cpt and denial_reason:
        enriched_query = build_enriched_query(payer, cpt, denial_reason, classification)
    else:
        enriched_query = query

    query_embedding = get_embedding(enriched_query)

    fetch_k = min(top_k * 4, 20)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=fetch_k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return []

    scored = []
    for doc, meta in zip(documents, metadatas):
        # CHANGED: also boost score if the chunk's payer matches the normalized request payer
        chunk_payer = normalize_payer(meta.get("payer", ""))
        payer_match_bonus = 2 if chunk_payer == normalized_payer else 0

        relevance_score = score_chunk_relevance(
            chunk_text=doc,
            cpt=cpt if cpt else "",
            denial_reason=denial_reason if denial_reason else ""
        ) + payer_match_bonus

        scored.append({
            "text": doc,
            "source": clean_source_label(meta.get("source", "Unknown")),
            "chunk_index": meta.get("chunk_index", 0),
            "payer": meta.get("payer", payer),
            "relevance_score": relevance_score
        })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)

    top_results = scored[:top_k]
    for r in top_results:
        r.pop("relevance_score")

    return top_results