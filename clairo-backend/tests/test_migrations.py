import sqlalchemy as sa

from app.database import Base
from app.migrations import run_migrations

# The schema exactly as production had it before migrations existed
# (created back then by Base.metadata.create_all).
LEGACY_DDL = """
CREATE TABLE denial_claims (
    id INTEGER NOT NULL PRIMARY KEY,
    payer VARCHAR, patient_id VARCHAR, cpt_codes VARCHAR, denial_reason VARCHAR,
    classification VARCHAR, billed_amount VARCHAR, denied_amount VARCHAR,
    service_date VARCHAR, risk_score FLOAT, appeal_generated INTEGER, created_at VARCHAR
)
"""


def _memory_engine():
    return sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool,
                            connect_args={"check_same_thread": False})


def test_migrations_preserve_existing_production_rows():
    engine = _memory_engine()
    with engine.begin() as conn:
        conn.execute(sa.text(LEGACY_DDL))
        conn.execute(sa.text(
            "INSERT INTO denial_claims (payer, cpt_codes, classification, risk_score, "
            "appeal_generated, created_at) VALUES ('UHC', '29881', 'medical_necessity', 80, 1, '2026-01-02')"
        ))
        run_migrations(connection=conn)

    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT payer, cpt_codes, risk_score, appeal_generated, status, user_id "
            "FROM denial_claims")).one()
    assert tuple(row) == ("UHC", "29881", 80.0, 1, "analyzed", None)   # legacy row kept & still "demo"


def test_migrations_are_idempotent():
    engine = _memory_engine()
    with engine.begin() as conn:
        run_migrations(connection=conn)
        run_migrations(connection=conn)   # already at head: must be a clean no-op
    assert "jobs" in sa.inspect(engine).get_table_names()


def test_migrations_match_the_sqlalchemy_models():
    """Catches the classic drift bug: editing a model without writing a migration."""
    engine = _memory_engine()
    with engine.begin() as conn:
        run_migrations(connection=conn)
    inspector = sa.inspect(engine)
    migrated_tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert migrated_tables == set(Base.metadata.tables)
    for name, table in Base.metadata.tables.items():
        migrated_cols = {c["name"] for c in inspector.get_columns(name)}
        assert migrated_cols == {c.name for c in table.columns}, f"column drift in {name}"
        migrated_idx = {i["name"] for i in inspector.get_indexes(name)}
        model_idx = {i.name for i in table.indexes}
        assert model_idx <= migrated_idx, f"missing indexes on {name}: {model_idx - migrated_idx}"


def test_downgrade_removes_new_tables_but_keeps_claims():
    from alembic import command
    from alembic.config import Config
    from app.migrations import _ALEMBIC_DIR

    engine = _memory_engine()
    with engine.begin() as conn:
        run_migrations(connection=conn)
        cfg = Config()
        cfg.set_main_option("script_location", _ALEMBIC_DIR)
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "0001")
    tables = set(sa.inspect(engine).get_table_names())
    assert "denial_claims" in tables and "users" not in tables and "jobs" not in tables
