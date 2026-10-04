from sqlalchemy import func, select

from app.models import AuditLog, DenialClaim


def _demo_count(db):
    return db.scalar(select(func.count(DenialClaim.id)).where(DenialClaim.user_id.is_(None)))


def test_seed_rejects_anonymous_and_non_admin_users(client, user, auth_headers):
    assert client.post("/analytics/seed").status_code == 403
    assert client.post("/analytics/seed", headers=auth_headers(user)).status_code == 403


def test_seed_works_for_admin_jwt_and_is_audited(client, admin, auth_headers, db):
    res = client.post("/analytics/seed", headers=auth_headers(admin))
    assert res.status_code == 200
    assert _demo_count(db) == 120
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "admin.seed_demo_data")).one()
    assert entry.actor_email == "admin@example.com" and entry.details == {"count": 120}


def test_seed_accepts_the_ops_api_key_only_when_configured(client, monkeypatch, db):
    monkeypatch.setattr("app.security.auth.ADMIN_API_KEY", "ops-secret")
    assert client.post("/analytics/seed", headers={"X-Admin-Key": "wrong"}).status_code == 403
    assert client.post("/analytics/seed", headers={"X-Admin-Key": "ops-secret"}).status_code == 200
    assert _demo_count(db) == 120

    monkeypatch.setattr("app.security.auth.ADMIN_API_KEY", "")
    # An unset server key must never match an empty/absent header.
    assert client.post("/analytics/seed", headers={"X-Admin-Key": ""}).status_code == 403


def test_seed_is_idempotent_unless_forced(client, admin, auth_headers, db):
    h = auth_headers(admin)
    client.post("/analytics/seed", headers=h)
    again = client.post("/analytics/seed", headers=h)
    assert "Already seeded" in again.json()["message"]
    assert client.post("/analytics/seed?force=true", headers=h).status_code == 200
    assert _demo_count(db) == 120


def test_reseeding_never_deletes_real_user_claims(client, admin, user, auth_headers, db):
    db.add(DenialClaim(payer="Cigna", user_id=user.id, status="analyzed", created_at="2026-03-01"))
    db.commit()
    client.post("/analytics/seed", headers=auth_headers(admin))
    client.post("/analytics/seed?force=true", headers=auth_headers(admin))
    assert db.scalar(select(func.count(DenialClaim.id)).where(DenialClaim.user_id == user.id)) == 1
