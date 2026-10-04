import os
import shutil
import tempfile

# Everything below must be set BEFORE any `app.*` import: config reads the
# environment at import time, and tests must never touch a dev/prod database,
# a real vector store, or real credentials.
_TMP = tempfile.mkdtemp(prefix="clairo_test_")
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["CHROMA_PATH"] = os.path.join(_TMP, "chroma")
os.environ["UPLOAD_FOLDER"] = os.path.join(_TMP, "uploads")
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-prod-0123456789"
os.environ["WORKER_ENABLED"] = "false"
os.environ["AUTO_MIGRATE"] = "false"
os.environ["LOG_JSON"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ.pop("INSFORGE_DATABASE_URL", None)
os.environ.pop("REDIS_URL", None)
# CI points this at a Postgres service container; locally it's a temp SQLite file.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or (
    "sqlite:///" + os.path.join(_TMP, "test.db").replace("\\", "/")
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.cache import cache  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.limiter import limiter  # noqa: E402
from app.migrations import run_migrations  # noqa: E402
from app.models import User  # noqa: E402
from app.models.user import ROLE_ADMIN, ROLE_USER  # noqa: E402
from app.security.auth import create_access_token, hash_password  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrated_database():
    """Build the schema with the real Alembic migrations (so they're tested)."""
    run_migrations()
    yield
    engine.dispose()
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_state():
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    limiter.reset()
    cache.clear()
    uploads = os.environ["UPLOAD_FOLDER"]
    if os.path.isdir(uploads):
        shutil.rmtree(uploads, ignore_errors=True)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def make_user(db):
    def _make(email="user@example.com", role=ROLE_USER, password="password123", active=True):
        user = User(email=email, password_hash=hash_password(password), role=role,
                    is_active=active)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    return _make


@pytest.fixture
def auth_headers():
    def _headers(user):
        return {"Authorization": f"Bearer {create_access_token(user)}"}
    return _headers


@pytest.fixture
def user(make_user):
    return make_user("alice@example.com")


@pytest.fixture
def other_user(make_user):
    return make_user("bob@example.com")


@pytest.fixture
def admin(make_user):
    return make_user("admin@example.com", role=ROLE_ADMIN)
