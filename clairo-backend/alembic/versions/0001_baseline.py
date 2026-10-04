"""Baseline: the denial_claims table as it existed before migrations.

Production already has this table (it was created by create_all), so every
step is guarded: a fresh database gets it created, an existing one is left
untouched and simply stamped at this revision.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("denial_claims"):
        return
    op.create_table(
        "denial_claims",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("payer", sa.String, nullable=True),
        sa.Column("patient_id", sa.String, nullable=True),
        sa.Column("cpt_codes", sa.String, nullable=True),
        sa.Column("denial_reason", sa.String, nullable=True),
        sa.Column("classification", sa.String, nullable=True),
        sa.Column("billed_amount", sa.String, nullable=True),
        sa.Column("denied_amount", sa.String, nullable=True),
        sa.Column("service_date", sa.String, nullable=True),
        sa.Column("risk_score", sa.Float, nullable=True),
        sa.Column("appeal_generated", sa.Integer, nullable=True),
        sa.Column("created_at", sa.String, nullable=True),
    )
    op.create_index("ix_denial_claims_id", "denial_claims", ["id"])


def downgrade() -> None:
    op.drop_table("denial_claims")
