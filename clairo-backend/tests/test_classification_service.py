from unittest.mock import MagicMock, patch

from app.services.classification_service import (
    ALLOWED_CATEGORIES,
    DEFAULT_CATEGORY,
    classify_denial,
)


def _mock_response(content: str):
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


@patch("app.services.classification_service.client")
def test_classify_denial_accepts_valid_category(mock_client):
    mock_client.chat.completions.create.return_value = _mock_response("prior_authorization")
    assert classify_denial({"denial_reason": "x"}) == "prior_authorization"


@patch("app.services.classification_service.client")
def test_classify_denial_normalizes_noisy_output(mock_client):
    mock_client.chat.completions.create.return_value = _mock_response(" Medical_Necessity.\n")
    assert classify_denial({}) == "medical_necessity"


@patch("app.services.classification_service.client")
def test_classify_denial_falls_back_on_unrecognized_category(mock_client):
    mock_client.chat.completions.create.return_value = _mock_response(
        "I think this is probably a coding issue"
    )
    result = classify_denial({})
    assert result == DEFAULT_CATEGORY
    assert result in ALLOWED_CATEGORIES


@patch("app.services.classification_service.client")
def test_classify_denial_falls_back_when_groq_call_fails(mock_client):
    mock_client.chat.completions.create.side_effect = RuntimeError("Groq down")
    assert classify_denial({}) == DEFAULT_CATEGORY
