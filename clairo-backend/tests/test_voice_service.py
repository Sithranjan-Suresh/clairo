from unittest.mock import MagicMock, patch

import pytest

from app.services.voice_service import VoiceProcessingError, parse_voice_intent, transcribe_audio


@patch("app.services.voice_service.client")
def test_transcribe_audio_wraps_failures(mock_client):
    mock_client.audio.transcriptions.create.side_effect = RuntimeError("Whisper down")
    with pytest.raises(VoiceProcessingError):
        transcribe_audio(b"fake-audio")


@patch("app.services.voice_service.client")
def test_parse_voice_intent_wraps_llm_failure(mock_client):
    mock_client.chat.completions.create.side_effect = RuntimeError("Groq down")
    with pytest.raises(VoiceProcessingError):
        parse_voice_intent("score claim 29881")


@patch("app.services.voice_service.client")
def test_parse_voice_intent_falls_back_on_bad_json(mock_client):
    choice = MagicMock()
    choice.message.content = "not valid json at all"
    response = MagicMock()
    response.choices = [choice]
    mock_client.chat.completions.create.return_value = response

    result = parse_voice_intent("some transcript")

    assert result["intent"] == "unknown"
    assert result["raw_transcript"] == "some transcript"
