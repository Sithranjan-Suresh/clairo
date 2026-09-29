from unittest.mock import MagicMock, patch

from app.services.risk_service import run_rule_based_scoring, score_claim


def test_prior_auth_code_raises_rule_score():
    result = run_rule_based_scoring(["29881"], "Aetna", "Complete documentation on file.")
    assert result["rule_based_score"] >= 25
    assert any("prior authorization" in flag for flag in result["rule_flags"])


def test_bundling_pair_is_flagged():
    result = run_rule_based_scoring(["29881", "29880"], "Aetna", "")
    assert any("bundled" in flag for flag in result["rule_flags"])


def test_strict_payer_and_missing_docs_stack():
    result = run_rule_based_scoring(["99999"], "UHC", "no documentation submitted")
    assert result["rule_based_score"] >= 25
    assert len(result["rule_flags"]) >= 2


def test_rule_score_is_capped_at_60():
    result = run_rule_based_scoring(["29881", "29880", "93306", "93307"], "UHC", "not documented")
    assert result["rule_based_score"] <= 60


def _mock_groq_response(content: str):
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@patch("app.services.risk_service.client")
def test_score_claim_combines_rule_and_llm_scores(mock_client):
    mock_client.chat.completions.create.return_value = _mock_groq_response(
        '{"llm_score": 10, "remediation": "Add physician notes."}'
    )

    result = score_claim(["29881"], "Aetna", "Complete documentation.")

    assert result["breakdown"]["rule_based_score"] == 25
    assert result["breakdown"]["llm_documentation_score"] == 10
    assert result["risk_score"] == 35
    assert result["risk_level"] == "LOW"


@patch("app.services.risk_service.client")
def test_score_claim_survives_llm_failure(mock_client):
    mock_client.chat.completions.create.side_effect = RuntimeError("Groq is down")

    result = score_claim(["29881"], "Aetna", "Complete documentation.")

    # Falls back to a default llm_score instead of raising and breaking the
    # /upload pipeline.
    assert result["breakdown"]["llm_documentation_score"] == 20
    assert "unavailable" in result["remediation"]


@patch("app.services.risk_service.client")
def test_score_claim_never_exceeds_100(mock_client):
    mock_client.chat.completions.create.return_value = _mock_groq_response(
        '{"llm_score": 40, "remediation": "x"}'
    )

    result = score_claim(["29881", "29880", "93306", "93307"], "UHC", "not documented")

    assert result["risk_score"] <= 100
    assert result["risk_level"] == "HIGH"
