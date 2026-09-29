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
