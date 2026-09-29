from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.limiter import limiter
from app.routes.insforge import router as insforge_router


def _build_app():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        lambda request, exc: JSONResponse(status_code=429, content={"error": "rate limited"}),
    )
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(insforge_router, prefix="/insforge")
    return app


def _mock_db_session():
    db = MagicMock()
    db.query.return_value.scalar.return_value = 0
    db.query.return_value.filter.return_value.scalar.return_value = 0
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    return db


@patch("app.routes.insforge.client")
@patch("app.routes.insforge.SessionLocal")
def test_agent_run_groq_failure_returns_clean_502_not_bare_500(mock_session_local, mock_client):
    """The Groq call here previously had no try/except at all, so a
    failure (e.g. the model-deprecation issue that broke this in
    production) raised unhandled -> bare 500 with no JSON body and no
    CORS headers. It should now be a clean 502 with a JSON detail."""
    mock_session_local.return_value = _mock_db_session()
    mock_client.chat.completions.create.side_effect = RuntimeError("model_not_found")

    limiter.reset()
    client = TestClient(_build_app())
    response = client.post("/insforge/agent-run", json={"query": "highest risk claims?"})
    limiter.reset()

    assert response.status_code == 502
    assert "detail" in response.json()
