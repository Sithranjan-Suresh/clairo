-- InsForge Migration: 001_create_denial_claims
-- Run with: npx @insforge/cli db migrations up --all
--
-- Creates the denial_claims table used by CLAIRO to persist every uploaded
-- denial letter and its AI-generated analysis results.

CREATE TABLE IF NOT EXISTS denial_claims (
    id              SERIAL PRIMARY KEY,
    payer           TEXT,
    patient_id      TEXT,
    cpt_codes       TEXT,
    denial_reason   TEXT,
    classification  TEXT,
    billed_amount   TEXT,
    denied_amount   TEXT,
    service_date    TEXT,
    risk_score      DOUBLE PRECISION,
    appeal_generated INTEGER DEFAULT 0,
    created_at      TEXT
);

-- Index for common analytics query patterns
CREATE INDEX IF NOT EXISTS idx_denial_claims_payer          ON denial_claims(payer);
CREATE INDEX IF NOT EXISTS idx_denial_claims_classification  ON denial_claims(classification);
CREATE INDEX IF NOT EXISTS idx_denial_claims_created_at      ON denial_claims(created_at);
