"""Users, documents, appeals, risk history, audit log, jobs, policy catalog.

Additive only: existing denial_claims rows are preserved (new columns are
nullable or carry a server default), so this is safe to run against the
live InsForge database.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _tz():
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("is_active", sa.Boolean, nullable=False),
            sa.Column("created_at", _tz(), nullable=False),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    claim_cols = {c["name"] for c in inspector.get_columns("denial_claims")}
    with op.batch_alter_table("denial_claims") as batch:
        if "user_id" not in claim_cols:
            batch.add_column(sa.Column(
                "user_id", sa.Integer,
                sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_claims_user_id"),
                nullable=True))
        if "status" not in claim_cols:
            batch.add_column(sa.Column(
                "status", sa.String(20), nullable=False, server_default="analyzed"))
        if "error_message" not in claim_cols:
            batch.add_column(sa.Column("error_message", sa.Text, nullable=True))
        if "updated_at" not in claim_cols:
            batch.add_column(sa.Column("updated_at", _tz(), nullable=True))

    claim_indexes = {i["name"] for i in sa.inspect(bind).get_indexes("denial_claims")}
    for name, cols in (
        ("ix_claims_payer", ["payer"]),
        ("ix_claims_classification", ["classification"]),
        ("ix_claims_risk_score", ["risk_score"]),
        ("ix_claims_status", ["status"]),
        ("ix_claims_user_id_id", ["user_id", "id"]),
    ):
        if name not in claim_indexes:
            op.create_index(name, "denial_claims", cols)

    if "documents" not in existing_tables:
        op.create_table(
            "documents",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("claim_id", sa.Integer,
                      sa.ForeignKey("denial_claims.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer,
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("original_filename", sa.String(255), nullable=True),
            sa.Column("stored_filename", sa.String(100), nullable=False),
            sa.Column("content_type", sa.String(100), nullable=True),
            sa.Column("size_bytes", sa.BigInteger, nullable=False),
            sa.Column("sha256", sa.String(64), nullable=False),
            sa.Column("created_at", _tz(), nullable=False),
        )
        op.create_index("ix_documents_claim_id", "documents", ["claim_id"])
        op.create_index("ix_documents_sha256", "documents", ["sha256"])

    if "appeals" not in existing_tables:
        op.create_table(
            "appeals",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("claim_id", sa.Integer,
                      sa.ForeignKey("denial_claims.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer,
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("letter_text", sa.Text, nullable=False),
            sa.Column("confidence_score", sa.Integer, nullable=False),
            sa.Column("confidence_rationale", sa.Text, nullable=True),
            sa.Column("citations", sa.JSON, nullable=True),
            sa.Column("model", sa.String(100), nullable=True),
            sa.Column("created_at", _tz(), nullable=False),
        )
        op.create_index("ix_appeals_claim_id", "appeals", ["claim_id"])

    if "risk_scores" not in existing_tables:
        op.create_table(
            "risk_scores",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("claim_id", sa.Integer,
                      sa.ForeignKey("denial_claims.id", ondelete="CASCADE"), nullable=False),
            sa.Column("score", sa.Float, nullable=False),
            sa.Column("level", sa.String(10), nullable=False),
            sa.Column("rule_score", sa.Integer, nullable=False),
            sa.Column("llm_score", sa.Integer, nullable=False),
            sa.Column("flags", sa.JSON, nullable=True),
            sa.Column("remediation", sa.Text, nullable=True),
            sa.Column("created_at", _tz(), nullable=False),
        )
        op.create_index("ix_risk_scores_claim_id", "risk_scores", ["claim_id"])

    if "audit_logs" not in existing_tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer,
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("actor_email", sa.String(255), nullable=True),
            sa.Column("action", sa.String(60), nullable=False),
            sa.Column("entity_type", sa.String(40), nullable=True),
            sa.Column("entity_id", sa.Integer, nullable=True),
            sa.Column("details", sa.JSON, nullable=True),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("request_id", sa.String(64), nullable=True),
            sa.Column("created_at", _tz(), nullable=False),
        )
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
        op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id"])

    if "jobs" not in existing_tables:
        op.create_table(
            "jobs",
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("type", sa.String(40), nullable=False),
            sa.Column("status", sa.String(12), nullable=False),
            sa.Column("claim_id", sa.Integer,
                      sa.ForeignKey("denial_claims.id", ondelete="CASCADE"), nullable=True),
            sa.Column("user_id", sa.Integer,
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("payload", sa.JSON, nullable=True),
            sa.Column("result", sa.JSON, nullable=True),
            sa.Column("error", sa.Text, nullable=True),
            sa.Column("attempts", sa.Integer, nullable=False),
            sa.Column("max_attempts", sa.Integer, nullable=False),
            sa.Column("run_after", _tz(), nullable=False),
            sa.Column("created_at", _tz(), nullable=False),
            sa.Column("started_at", _tz(), nullable=True),
            sa.Column("finished_at", _tz(), nullable=True),
        )
        op.create_index("ix_jobs_status_run_after", "jobs", ["status", "run_after"])

    if "payer_policies" not in existing_tables:
        op.create_table(
            "payer_policies",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("payer", sa.String(100), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("source_file", sa.String(500), nullable=False, unique=True),
            sa.Column("chunk_count", sa.Integer, nullable=False),
            sa.Column("synced_at", _tz(), nullable=False),
        )
        op.create_index("ix_payer_policies_payer", "payer_policies", ["payer"])


def downgrade() -> None:
    for table in ("payer_policies", "jobs", "audit_logs", "risk_scores",
                  "appeals", "documents"):
        op.drop_table(table)
    for name in ("ix_claims_user_id_id", "ix_claims_status", "ix_claims_risk_score",
                 "ix_claims_classification", "ix_claims_payer"):
        op.drop_index(name, table_name="denial_claims")
    with op.batch_alter_table("denial_claims") as batch:
        for col in ("updated_at", "error_message", "status", "user_id"):
            batch.drop_column(col)
    op.drop_table("users")
