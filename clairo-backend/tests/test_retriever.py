from app.rag.retriever import (
    clean_source_label,
    normalize_payer,
    score_chunk_relevance,
)


def test_normalize_payer_handles_case_spacing_and_punctuation():
    assert normalize_payer("UnitedHealthCare") == "uhc"
    assert normalize_payer("United Health Care") == "uhc"
    assert normalize_payer("Blue Cross Blue Shield") == "bcbs"
    assert normalize_payer("Anthem") == "bcbs"
    assert normalize_payer("Cigna Healthspring") == "cigna"


def test_normalize_payer_unknown_passes_through_normalized():
    assert normalize_payer("SomeRandomPayer") == "somerandompayer"


def test_clean_source_label_strips_path_extension_and_underscores():
    assert clean_source_label("app/data/policies/aetna_medical_necessity.pdf") == "Aetna Medical Necessity"
    assert clean_source_label("") == "Unknown Policy"
    assert clean_source_label(None) == "Unknown Policy"


def test_score_chunk_relevance_rewards_clinical_signal():
    strong = score_chunk_relevance(
        "This procedure is medically necessary based on clinical criteria for CPT 29881.",
        cpt="29881",
        denial_reason="medical necessity",
    )
    weak = score_chunk_relevance(
        "This document is for informational purposes only and does not constitute medical advice.",
        cpt="29881",
        denial_reason="medical necessity",
    )
    assert strong > weak


def test_retrieval_does_not_waste_citation_slots_on_duplicate_chunks():
    from unittest.mock import patch

    from app.rag import retriever

    dup = "Prior authorization is required for arthroscopic procedures."
    fake = {
        "documents": [[dup, dup, "Different criterion about physical therapy.", dup]],
        "metadatas": [[{"payer": "AETNA", "source": "a.pdf", "chunk_index": i} for i in range(4)]],
    }
    with patch.object(retriever.collection, "query", return_value=fake), \
         patch.object(retriever, "get_embedding", return_value=[0.0]):
        results = retriever._retrieve_policy("Aetna", "q", top_k=3)
    assert [r["text"] for r in results].count(dup) == 1
    assert len(results) == 2
