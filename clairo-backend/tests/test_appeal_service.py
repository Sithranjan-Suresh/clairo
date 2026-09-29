from app.services.appeal_service import get_appeal_viability, safe_json_parse


def test_safe_json_parse_handles_code_fences():
    text = '```json\n{"appeal_letter": "hi", "confidence_score": 80}\n```'
    result = safe_json_parse(text)
    assert result["appeal_letter"] == "hi"
    assert result["confidence_score"] == 80


def test_safe_json_parse_falls_back_on_garbage():
    result = safe_json_parse("not json at all")
    assert result["confidence_score"] == 0
    assert "Failed" in result["appeal_letter"]


def test_appeal_viability_strong_case():
    result = get_appeal_viability(90, "medical_necessity", "Aetna")
    assert result["appeal_strength"] == "Strong"
    assert result["appeal_strength_score"] > 90  # medical_necessity gets a +5 bonus


def test_appeal_viability_strict_payer_penalty():
    strict = get_appeal_viability(80, "medical_necessity", "UHC")
    lenient = get_appeal_viability(80, "medical_necessity", "Aetna")
    assert strict["appeal_strength_score"] < lenient["appeal_strength_score"]


def test_appeal_viability_weak_category_and_score_clamped_to_range():
    result = get_appeal_viability(5, "timely_filing", "UHC")
    assert result["appeal_strength"] == "Weak"
    assert 0 <= result["appeal_strength_score"] <= 100
