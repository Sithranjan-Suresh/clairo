import json
import logging
from unittest.mock import MagicMock, patch

from app import observability
from app.observability import JsonFormatter, client_ip, request_id_var


def test_health_checks_the_database(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": True, "cache": "memory"}


def test_every_response_carries_a_request_id(client):
    res = client.get("/")
    assert len(res.headers["x-request-id"]) >= 8
    echoed = client.get("/", headers={"X-Request-ID": "trace-abc-123"})
    assert echoed.headers["x-request-id"] == "trace-abc-123"


def test_security_headers_present(client):
    res = client.get("/")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"


def test_metrics_endpoint_is_admin_only(client, user, admin, auth_headers, monkeypatch):
    assert client.get("/metrics").status_code == 403
    assert client.get("/metrics", headers=auth_headers(user)).status_code == 403
    ok = client.get("/metrics", headers=auth_headers(admin))
    assert ok.status_code == 200
    assert "clairo_http_requests_total" in ok.text

    monkeypatch.setattr("app.security.auth.ADMIN_API_KEY", "ops-key")
    assert client.get("/metrics", headers={"X-Admin-Key": "ops-key"}).status_code == 200
    assert client.get("/metrics", headers={"X-Admin-Key": "nope"}).status_code == 403


def test_metrics_record_routes_by_template_not_raw_path(client, user, auth_headers, admin):
    client.get("/claims/123456", headers=auth_headers(user))     # 404 but a matched route
    text = client.get("/metrics", headers=auth_headers(admin)).text
    assert 'route="/claims/{claim_id}"' in text                  # bounded label cardinality
    assert "123456" not in text


def test_llm_metrics_are_recorded_per_task():
    from app.services.groq_services import _InstrumentedClient

    inner = MagicMock()
    inner.chat.completions.create.return_value = "response"
    wrapped = _InstrumentedClient(inner)
    before = observability.LLM_CALLS.labels("unit_test", "ok")._value.get()
    assert wrapped.chat.completions.create(model="m", task="unit_test") == "response"
    assert observability.LLM_CALLS.labels("unit_test", "ok")._value.get() == before + 1
    inner.chat.completions.create.assert_called_once_with(model="m")   # `task` isn't leaked to Groq

    inner.chat.completions.create.side_effect = RuntimeError("boom")
    before_err = observability.LLM_CALLS.labels("unit_test", "error")._value.get()
    try:
        wrapped.chat.completions.create(model="m", task="unit_test")
    except RuntimeError:
        pass
    assert observability.LLM_CALLS.labels("unit_test", "error")._value.get() == before_err + 1


def test_json_log_lines_include_request_id_and_context():
    token = request_id_var.set("req-42")
    try:
        record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello %s", ("world",), None)
        record.ctx = {"status": 200}
        line = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert line["msg"] == "hello world" and line["request_id"] == "req-42" and line["status"] == 200


def test_client_ip_prefers_first_forwarded_hop():
    req = MagicMock()
    req.headers = {"x-forwarded-for": "203.0.113.9, 10.0.0.1"}
    assert client_ip(req) == "203.0.113.9"
    req.headers = {}
    req.client.host = "127.0.0.1"
    assert client_ip(req) == "127.0.0.1"


def test_rate_limits_are_per_user_not_per_shared_ip(client, make_user, auth_headers):
    a, b = make_user("a@example.com"), make_user("b@example.com")
    with patch("app.routes.rag.retrieve_policy", return_value=[]):
        params = {"payer": "Aetna", "cpt": "29881", "denial_reason": "x"}
        codes = [client.get("/rag/retrieve", params=params, headers=auth_headers(a)).status_code
                 for _ in range(31)]
        assert codes.count(200) == 30 and codes[-1] == 429       # user A exhausted /rag/retrieve
        assert client.get("/rag/retrieve", params=params, headers=auth_headers(b)).status_code == 200
