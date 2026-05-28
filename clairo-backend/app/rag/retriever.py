from app.rag.vectorstore import collection
from app.rag.embedder import get_embedding


PAYER_ALIASES = {
    "uhc": "uhc",
    "unitedhealthcare": "uhc",
    "united": "uhc",
    "aetna": "aetna",
    "bcbs": "bcbs",
    "bluecross": "bcbs",
    "blue cross": "bcbs",
    "cigna": "cigna",
    "humana": "humana",
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


def normalize_payer(payer: str) -> str:
    return PAYER_ALIASES.get(payer.lower().strip(), payer.lower().strip())


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

    # Reward chunks that mention the specific CPT code
    if cpt_lower in text_lower:
        score += 3

    # Reward chunks with medical necessity language
    if "medical necessity" in text_lower or "medically necessary" in text_lower:
        score += 3

    # Reward chunks with criteria/indications language
    if "criteria" in text_lower or "indication" in text_lower:
        score += 2

    # Reward chunks with coverage decision language
    if "proven" in text_lower or "not medically necessary" in text_lower or "covered" in text_lower:
        score += 2

    # Reward chunks that mention the denial reason keywords
    for keyword in denial_lower.split():
        if len(keyword) > 4 and keyword in text_lower:
            score += 1

    # Penalize generic boilerplate chunks
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


def retrieve_policy(payer: str, query: str, top_k: int = 3, classification: str = None, cpt: str = "", denial_reason: str = "") -> list:

    normalized_payer = normalize_payer(payer)

    # Build enriched query if cpt and denial_reason provided
    if cpt and denial_reason:
        enriched_query = build_enriched_query(payer, cpt, denial_reason, classification)
    else:
        enriched_query = query

    query_embedding = get_embedding(enriched_query)

    # Retrieve more than needed so we can rerank
    fetch_k = min(top_k * 4, 20)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=fetch_k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return []

    # Score and rerank chunks
    scored = []
    for doc, meta in zip(documents, metadatas):
        relevance_score = score_chunk_relevance(
            chunk_text=doc,
            cpt=cpt if cpt else "",
            denial_reason=denial_reason if denial_reason else ""
        )
        scored.append({
            "text": doc,
            "source": meta.get("source", "Unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "payer": meta.get("payer", payer),
            "relevance_score": relevance_score
        })

    # Sort by relevance score descending
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)

    # Return top_k after reranking, drop the score from the output
    top_results = scored[:top_k]
    for r in top_results:
        r.pop("relevance_score")

    return top_results