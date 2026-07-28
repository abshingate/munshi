-- Munshi knowledge base — company history (ADR-0020, extended)
--
-- Migration 001 indexes DOCUMENTS: "find the ARTH invoice".
-- This migration adds FACTS: "what did we pay ARTH in FY 2022-23, and does
-- the bank agree with the books?"
--
-- Those are different questions and need different shapes. A document store
-- cannot sum, reconcile, or tell you what is missing. The whole point of
-- putting this in PostgreSQL rather than a vector store is that the same
-- database can do both, and join across them.
--
-- Design notes:
--   * bank_transaction is EVIDENCE — what the bank says moved. Immutable fact.
--   * tally_voucher is an ASSERTION — what the books claim. May be wrong,
--     may be missing entirely.
--   * The gap between them is the finding. Hence recon_match, which records
--     both agreement AND its absence.
--   * period tables carry the statutory/filing timeline so "what happened in
--     FY 2019-20?" has an answer even where documents are sparse.
--   * Everything is company-agnostic: no Exadatum-specific columns, no
--     India-specific enums beyond free-text labels.

BEGIN;

-- ---------------------------------------------------------------------------
-- Financial years. Explicit table, not derived, because the FY boundary is
-- jurisdiction-specific (India: 1 Apr – 31 Mar) and every query needs it.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fin_year (
    label       TEXT PRIMARY KEY,          -- '2025-26'
    starts_on   DATE NOT NULL,
    ends_on     DATE NOT NULL,
    status      TEXT,                      -- 'open' | 'audited' | 'filed' | 'closed'
    notes       TEXT
);

COMMENT ON TABLE fin_year IS 'Financial-year calendar. Populate for every year the company has existed, including years with no data — absence is itself an answer.';

-- ---------------------------------------------------------------------------
-- Bank accounts and transactions — the evidence layer.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bank_account (
    id              BIGSERIAL PRIMARY KEY,
    account_number  TEXT NOT NULL,
    bank_name       TEXT,
    label           TEXT,                  -- 'primary current account'
    opened_on       DATE,
    closed_on       DATE,                  -- closed accounts still hold history
    UNIQUE (account_number)
);

CREATE TABLE IF NOT EXISTS bank_transaction (
    id              BIGSERIAL PRIMARY KEY,
    account_id      BIGINT NOT NULL REFERENCES bank_account(id),
    txn_date        DATE   NOT NULL,
    value_date      DATE,
    description     TEXT   NOT NULL,       -- raw narration, never cleaned away
    reference       TEXT,                  -- cheque/UTR/UPI ref where present
    debit           NUMERIC(18,2),         -- money out
    credit          NUMERIC(18,2),         -- money in
    balance         NUMERIC(18,2),         -- running balance as printed
    counterparty    TEXT,                  -- parsed from narration, best-effort
    source_document BIGINT REFERENCES kb_document(id),   -- which statement this came from
    row_hash        TEXT NOT NULL,         -- idempotency: same line never loaded twice
    UNIQUE (row_hash)
);

COMMENT ON TABLE bank_transaction IS 'What the bank says happened. The strongest evidence available: money that moved is a fact, a ledger entry is only an assertion about it.';
COMMENT ON COLUMN bank_transaction.description IS 'Raw narration exactly as printed. Parsing is lossy; the original must survive for audit.';

CREATE INDEX IF NOT EXISTS bank_txn_date_idx    ON bank_transaction (txn_date);
CREATE INDEX IF NOT EXISTS bank_txn_account_idx ON bank_transaction (account_id, txn_date);
CREATE INDEX IF NOT EXISTS bank_txn_party_idx   ON bank_transaction USING GIN (counterparty gin_trgm_ops);
CREATE INDEX IF NOT EXISTS bank_txn_desc_idx    ON bank_transaction USING GIN (to_tsvector('english', description));

-- ---------------------------------------------------------------------------
-- Tally: ledgers and vouchers — the assertion layer.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tally_ledger (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    parent      TEXT,                      -- Tally group: 'Sundry Creditors', ...
    is_party    BOOLEAN,                   -- vendor/customer vs nominal account
    UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS tally_voucher (
    id              BIGSERIAL PRIMARY KEY,
    voucher_date    DATE   NOT NULL,
    voucher_type    TEXT,                  -- 'Payment' | 'Receipt' | 'Journal' | 'Sales' | ...
    voucher_number  TEXT,
    narration       TEXT,
    fin_year        TEXT REFERENCES fin_year(label),
    extracted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    row_hash        TEXT NOT NULL,
    UNIQUE (row_hash)
);

CREATE TABLE IF NOT EXISTS tally_entry (
    id          BIGSERIAL PRIMARY KEY,
    voucher_id  BIGINT NOT NULL REFERENCES tally_voucher(id) ON DELETE CASCADE,
    ledger_id   BIGINT REFERENCES tally_ledger(id),
    ledger_name TEXT   NOT NULL,           -- kept even when the ledger row is unknown
    amount      NUMERIC(18,2) NOT NULL,    -- Tally convention: debit negative, credit positive
    is_debit    BOOLEAN
);

CREATE INDEX IF NOT EXISTS tally_voucher_date_idx  ON tally_voucher (voucher_date);
CREATE INDEX IF NOT EXISTS tally_voucher_fy_idx    ON tally_voucher (fin_year);
CREATE INDEX IF NOT EXISTS tally_entry_ledger_idx  ON tally_entry (ledger_name);
CREATE INDEX IF NOT EXISTS tally_entry_voucher_idx ON tally_entry (voucher_id);

-- ---------------------------------------------------------------------------
-- Reconciliation: where evidence and assertion meet — or fail to.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recon_match (
    id              BIGSERIAL PRIMARY KEY,
    bank_txn_id     BIGINT REFERENCES bank_transaction(id),
    voucher_id      BIGINT REFERENCES tally_voucher(id),
    match_type      TEXT NOT NULL,   -- 'exact' | 'probable' | 'manual'
                                     -- 'bank-only'  = money moved, no voucher  → MISSING ENTRY
                                     -- 'books-only' = voucher, no bank line    → accrual or ERROR
    confidence      NUMERIC(3,2),
    matched_on      TIMESTAMPTZ NOT NULL DEFAULT now(),
    note            TEXT,
    CHECK (bank_txn_id IS NOT NULL OR voucher_id IS NOT NULL)
);

COMMENT ON TABLE recon_match IS 'Records agreement AND its absence. A bank-only row is a missing book entry; a books-only row is an accrual or an error. The exceptions are the product.';

-- ---------------------------------------------------------------------------
-- Findings: the durable output of verification work.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS finding (
    id              BIGSERIAL PRIMARY KEY,
    ref             TEXT UNIQUE,           -- 'E001'
    fin_year        TEXT REFERENCES fin_year(label),
    category        TEXT NOT NULL,         -- 'missing-entry' | 'tds-default' | 'evidence-gap' | ...
    severity        TEXT,                  -- 'high' | 'medium' | 'low'
    description     TEXT NOT NULL,
    amount          NUMERIC(18,2),
    evidence        TEXT,                  -- what proves it: cite documents/transactions
    status          TEXT NOT NULL DEFAULT 'open',
    action          TEXT,
    opened_on       DATE NOT NULL DEFAULT CURRENT_DATE,
    resolved_on     DATE
);

-- ---------------------------------------------------------------------------
-- Coverage: what we hold, and — critically — what we know we are missing.
-- An assistant that cannot say "I have no data for FY 2016-17" will instead
-- answer confidently from nothing. This table is what makes honesty possible.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coverage (
    id              BIGSERIAL PRIMARY KEY,
    fin_year        TEXT REFERENCES fin_year(label),
    evidence_type   TEXT NOT NULL,         -- 'bank-statement' | 'tally' | 'financials' | 'itr' | 'gst' | 'tds-return' | 'payroll'
    status          TEXT NOT NULL,         -- 'held' | 'partial' | 'missing' | 'not-applicable'
    detail          TEXT,
    checked_on      DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (fin_year, evidence_type)
);

COMMENT ON TABLE coverage IS 'What evidence exists per year. Queried BEFORE answering, so the assistant can say "no data for that year" instead of inventing one.';

-- ---------------------------------------------------------------------------
-- Convenience views
-- ---------------------------------------------------------------------------

-- Money moved with no voucher behind it: the highest-value exception class.
CREATE OR REPLACE VIEW v_unmatched_bank AS
SELECT b.id, b.txn_date, b.description, b.debit, b.credit, b.counterparty,
       a.account_number
FROM bank_transaction b
JOIN bank_account a ON a.id = b.account_id
LEFT JOIN recon_match m ON m.bank_txn_id = b.id AND m.voucher_id IS NOT NULL
WHERE m.id IS NULL
ORDER BY b.txn_date;

-- Everything known about a counterparty, from both sides at once.
CREATE OR REPLACE VIEW v_party_activity AS
SELECT counterparty AS party,
       date_trunc('year', txn_date)::date AS yr,
       count(*)         AS txn_count,
       sum(debit)       AS paid_out,
       sum(credit)      AS received
FROM bank_transaction
WHERE counterparty IS NOT NULL
GROUP BY 1, 2;

INSERT INTO kb_schema_version (version, description)
VALUES (3, 'company history: bank, tally, reconciliation, findings, coverage')
ON CONFLICT (version) DO NOTHING;

COMMIT;
