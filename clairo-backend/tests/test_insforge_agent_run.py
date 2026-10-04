from unittest.mock import MagicMock, patch

from app.models import DenialClaim

LLM_JSON = '{"summary": "UHC is riskiest.", "key_findings": ["a"], "recommendation": "Fix docs", "data_source": "x"}'


def _llm_returning(text):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = text
    return resp


def test_agent_run_requires_auth(client):
    assert client.post("/insforge/agent-run", json={"query": "hi"}).status_code == 401


@patch("app.routes.insforge.client")
def test_groq_failure_returns_clean_502_not_bare_500(mock_client, client, user, auth_headers):
    """Previously an unhandled Groq error escaped as a bare 500 with no JSON body and no
    CORS headers, which browsers reported as a network failure."""
    mock_client.chat.completions.create.side_effect = RuntimeError("model_not_found")
    res = client.post("/insforge/agent-run", json={"query": "highest risk claims?"},
                      headers=auth_headers(user))
    assert res.status_code == 502 and "detail" in res.json()


@patch("app.routes.insforge.client")
def test_agent_only_sees_data_the_caller_may_see(mock_client, client, user, other_user, auth_headers, db):
    db.add_all([
        DenialClaim(payer="UHC", risk_score=90, user_id=user.id, status="analyzed", cpt_codes="1"),
        DenialClaim(payer="SECRETPAYER", risk_score=99, user_id=other_user.id,
                    status="analyzed", cpt_codes="2"),
    ])
    db.commit()
    mock_client.chat.completions.create.return_value = _llm_returning(LLM_JSON)
    res = client.post("/insforge/agent-run", json={"query": "risk?"}, headers=auth_headers(user))
    assert res.status_code == 200
    assert res.json()["insforge_context"]["total_claims"] == 1
    prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "SECRETPAYER" not in prompt                      # no cross-tenant leakage into the LLM


@patch("app.routes.insforge.client")
def test_non_json_llm_output_degrades_to_plain_summary(mock_client, client, user, auth_headers):
    mock_client.chat.completions.create.return_value = _llm_returning("not json at all")
    res = client.post("/insforge/agent-run", json={"query": "x"}, headers=auth_headers(user))
    assert res.status_code == 200
    assert res.json()["agent_response"]["summary"] == "not json at all"


def test_status_and_live_feed_are_scoped(client, user, other_user, auth_headers, db):
    db.add_all([
        DenialClaim(payer="Mine", risk_score=75, user_id=user.id, status="analyzed", cpt_codes="1"),
        DenialClaim(payer="Theirs", risk_score=75, user_id=other_user.id, status="analyzed", cpt_codes="1"),
        DenialClaim(payer="Demo", risk_score=10, user_id=None, status="analyzed", cpt_codes="1"),
    ])
    db.commit()
    status = client.get("/insforge/status", headers=auth_headers(user)).json()
    assert status["live_stats"]["total_claims"] == 2 and status["live_stats"]["high_risk_claims"] == 1
    feed = client.get("/insforge/live-claims", headers=auth_headers(user)).json()
    assert {c["payer"] for c in feed["claims"]} == {"Mine", "Demo"}
