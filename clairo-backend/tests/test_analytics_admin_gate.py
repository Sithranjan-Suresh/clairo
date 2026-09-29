import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.limiter import limiter
from app.routes.analytics import router as analytics_router


def _build_app():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        lambda request, exc: JSONResponse(status_code=429, content={"error": "rate limited"}),
    )
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(analytics_router, prefix="/analytics")
    return app


@pytest.fixture
def client():
    limiter.reset()
    yield TestClient(_build_app())
    limiter.reset()


def _mock_db_session():
    db = MagicMock()
    db.query.return_value.count.return_value = 0
    return db


@patch.dict(os.environ, {"ADMIN_API_KEY": "super-secret"})
@patch("app.routes.analytics.SessionLocal")
def test_seed_rejected_without_admin_key(mock_session_local, client):
    mock_session_local.return_value = _mock_db_session()
    response = client.post("/analytics/seed")
    assert response.status_code == 403


@patch.dict(os.environ, {"ADMIN_API_KEY": "super-secret"})
@patch("app.routes.analytics.SessionLocal")
def test_seed_rejected_with_wrong_admin_key(mock_session_local, client):
    mock_session_local.return_value = _mock_db_session()
    response = client.post("/analytics/seed", headers={"X-Admin-Key": "wrong"})
    assert response.status_code == 403


@patch.dict(os.environ, {"ADMIN_API_KEY": "super-secret"})
@patch("app.routes.analytics.SessionLocal")
def test_seed_accepted_with_correct_admin_key(mock_session_local, client):
    mock_session_local.return_value = _mock_db_session()
    response = client.post("/analytics/seed", headers={"X-Admin-Key": "super-secret"})
    assert response.status_code == 200


@patch.dict(os.environ, {}, clear=False)
@patch("app.routes.analytics.SessionLocal")
def test_seed_allowed_without_admin_key_when_unset(mock_session_local, client, monkeypatch):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    mock_session_local.return_value = _mock_db_session()
    response = client.post("/analytics/seed")
    assert response.status_code == 200
