from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select

from app.config import JWT_ALGORITHM, JWT_SECRET
from app.models import AuditLog, User
from app.models.user import ROLE_ADMIN, ROLE_USER
from app.security.auth import hash_password, verify_password
from app.services import auth_service


def _register(client, email="new@example.com", password="correct-horse-1"):
    return client.post("/auth/register", json={"email": email, "password": password})


def test_register_returns_token_and_creates_plain_user(client, db):
    res = _register(client)
    assert res.status_code == 201
    body = res.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["role"] == ROLE_USER
    assert "password" not in str(body)


def test_register_never_grants_admin_even_for_admin_email(client, db, monkeypatch):
    monkeypatch.setattr(auth_service, "ADMIN_EMAIL", "boss@example.com")
    res = _register(client, "boss@example.com")
    assert res.json()["user"]["role"] == ROLE_USER


def test_register_normalizes_email_and_rejects_duplicates(client):
    assert _register(client, "Mixed@Example.com").status_code == 201
    dup = _register(client, "mixed@example.com")
    assert dup.status_code == 409


def test_register_validates_input(client):
    assert _register(client, "not-an-email").status_code == 422
    assert _register(client, "ok@example.com", "short").status_code == 422
    assert _register(client, "ok@example.com", "x" * 200).status_code == 422


def test_registration_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(auth_service, "ALLOW_REGISTRATION", False)
    assert _register(client).status_code == 403


def test_login_success_and_me(client):
    _register(client, "me@example.com", "password-123")
    res = client.post("/auth/login", json={"email": "ME@example.com", "password": "password-123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "me@example.com"


def test_login_failures_are_indistinguishable(client):
    _register(client, "real@example.com", "password-123")
    wrong_pw = client.post("/auth/login", json={"email": "real@example.com", "password": "nope-nope"})
    no_user = client.post("/auth/login", json={"email": "ghost@example.com", "password": "nope-nope"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_inactive_user_cannot_login_or_use_existing_token(client, make_user, auth_headers, db):
    user = make_user("gone@example.com", password="password-123")
    headers = auth_headers(user)
    assert client.get("/auth/me", headers=headers).status_code == 200
    user.is_active = False
    db.commit()
    assert client.get("/auth/me", headers=headers).status_code == 401
    res = client.post("/auth/login", json={"email": "gone@example.com", "password": "password-123"})
    assert res.status_code == 401


def test_protected_routes_reject_missing_garbage_and_expired_tokens(client, user):
    assert client.get("/claims").status_code == 401
    assert client.get("/claims", headers={"Authorization": "Bearer garbage"}).status_code == 401
    expired = jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )
    assert client.get("/claims", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    forged = jwt.encode({"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                        "w" * 40, algorithm=JWT_ALGORITHM)
    assert client.get("/claims", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_password_hashing_handles_long_passwords_and_is_salted():
    long_pw = "a" * 120
    h1, h2 = hash_password(long_pw), hash_password(long_pw)
    assert h1 != h2
    assert verify_password(long_pw, h1)
    assert not verify_password("a" * 119 + "b", h1)   # bcrypt alone would truncate at 72 bytes


def test_admin_role_is_enforced(client, user, admin, auth_headers):
    assert client.get("/audit-logs", headers=auth_headers(user)).status_code == 403
    assert client.get("/audit-logs", headers=auth_headers(admin)).status_code == 200
    assert client.get("/audit-logs").status_code == 401


def test_bootstrap_admin_creates_and_updates_account(db, monkeypatch):
    monkeypatch.setattr(auth_service, "ADMIN_EMAIL", "root@example.com")
    monkeypatch.setattr(auth_service, "ADMIN_PASSWORD", "first-password")
    created = auth_service.bootstrap_admin(db)
    assert created.role == ROLE_ADMIN

    monkeypatch.setattr(auth_service, "ADMIN_PASSWORD", "rotated-password")
    auth_service.bootstrap_admin(db)
    db.expire_all()
    row = db.scalar(select(User).where(User.email == "root@example.com"))
    assert verify_password("rotated-password", row.password_hash)
    assert db.scalar(select(User).where(User.role == ROLE_ADMIN)) is not None


def test_bootstrap_admin_is_noop_without_credentials(db, monkeypatch):
    monkeypatch.setattr(auth_service, "ADMIN_EMAIL", "")
    assert auth_service.bootstrap_admin(db) is None


def test_auth_events_are_audited(client, db):
    _register(client, "audited@example.com", "password-123")
    client.post("/auth/login", json={"email": "audited@example.com", "password": "password-123"})
    client.post("/auth/login", json={"email": "audited@example.com", "password": "wrong-wrong"})
    actions = [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id)).all()]
    assert actions == ["auth.register", "auth.login", "auth.login_failed"]
    failed = db.scalars(select(AuditLog).where(AuditLog.action == "auth.login_failed")).one()
    assert failed.actor_email == "audited@example.com"
    assert failed.request_id   # correlated with the access log


def test_login_is_rate_limited(client):
    statuses = [
        client.post("/auth/login", json={"email": "x@example.com", "password": "bad-password"}).status_code
        for _ in range(12)
    ]
    assert statuses.count(401) == 10 and statuses[-1] == 429
