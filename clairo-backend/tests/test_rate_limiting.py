from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.limiter import limiter
from app.routes.rag import router as rag_router


def _build_app():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        lambda request, exc: JSONResponse(status_code=429, content={"error": "rate limited"}),
    )
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(rag_router, prefix="/rag")
    return app


@patch("app.routes.rag.retrieve_policy", return_value=[])
def test_requests_beyond_the_limit_get_429(mock_retrieve):
    limiter.reset()
    client = TestClient(_build_app())
    params = {"payer": "Aetna", "cpt": "29881", "denial_reason": "x"}

    # /rag/retrieve is limited to 30/minute.
    statuses = [client.get("/rag/retrieve", params=params).status_code for _ in range(31)]

    assert statuses.count(200) == 30
    assert statuses[-1] == 429
    limiter.reset()
