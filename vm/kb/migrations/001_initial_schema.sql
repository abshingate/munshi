-- Munshi knowledge base — initial schema
-- ADR-0020: PostgreSQL + pgvector, one store for structured, full-text and
-- semantic search over a company's documents and correspondence.
--
-- Design notes:
--   * Documents on disk stay the source of truth (ADR-0012). Every row keeps
--     source_path so you can always get back to the original file.
--   * content_hash makes ingestion idempotent: re-running an import never
--     duplicates, and a changed file is detected without reading it twice.
--   * Chunks, not whole documents, carry embeddings — a 40-page statement
--     has many distinct topics and one vector cannot represent them all.
--   * Nothing here is India- or Tally-specific. `party` and `doc_type` are
--     free text so any company in any jurisdiction can use their own labels.

-- pgvector is OPTIONAL. Where it is unavailable (some packaged PostgreSQL
-- builds ship without it), everything except semantic search still works:
-- SQL filters, full-text search, and the whole document/chunk model.
-- Migration 002 adds the embedding column once the extension is installed.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
    RAISE NOTICE 'pgvector enabled: semantic search available';
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'pgvector NOT available (%). SQL + full-text search will work; '
                  'run migration 002 after installing it to enable semantic search.',
                  SQLERRM;
END $$;

CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy name matching ("ARTH" ~ "Arth & Associates")

-- ---------------------------------------------------------------------------
-- sources: where a batch of documents came from. One row per import run.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kb_source (
    id              BIGSERIAL PRIMARY KEY,
    kind            TEXT        NOT NULL,           -- 'gmail-takeout' | 'drive-takeout' | 'filesystem' | 'tally' | 'manual'
    label           TEXT,                           -- human note: "Takeout 2026-07-28, business label only"
    location        TEXT,                           -- path or bucket the import read from
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    document_count  INTEGER     NOT NULL DEFAULT 0,
    notes           TEXT
);

COMMENT ON TABLE kb_source IS 'One row per ingestion run; lets you trace any document back to the export it came from and re-run cleanly.';

-- ---------------------------------------------------------------------------
-- documents: one row per email, attachment, file, or exported report.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kb_document (
    id              BIGSERIAL PRIMARY KEY,
    source_id       BIGINT      REFERENCES kb_source(id) ON DELETE SET NULL,

    -- identity / dedup
    content_hash    TEXT        NOT NULL,           -- sha256 of raw bytes; ingestion is idempotent on this
    source_path     TEXT        NOT NULL,           -- absolute or repo-relative path to the original on disk
    filename        TEXT,

    -- classification (deliberately free text — every company labels differently)
    doc_type        TEXT,                           -- 'email' | 'invoice' | 'bank-statement' | 'return' | 'challan' | 'contract' | ...
    mime_type       TEXT,

    -- the "who / when / what" that makes finance questions answerable
    doc_date        DATE,                           -- date of the document itself, not the file mtime
    party           TEXT,                           -- counterparty: vendor, customer, authority
    subject         TEXT,
    sender          TEXT,
    recipients      TEXT[],

    -- money, when the document is about a transaction
    amount          NUMERIC(18,2),
    currency        TEXT        DEFAULT 'INR',

    -- email threading (null for non-email documents)
    message_id      TEXT,
    thread_id       TEXT,
    in_reply_to     TEXT,

    -- extracted text of the whole document (chunks live separately)
    body_text       TEXT,
    page_count      INTEGER,

    -- open-ended room for source-specific fields without schema churn
    metadata        JSONB       NOT NULL DEFAULT '{}'::jsonb,

    -- full-text search vector, maintained by trigger below
    tsv             TSVECTOR,

    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (content_hash)
);

COMMENT ON COLUMN kb_document.content_hash IS 'sha256 of the raw file bytes. The uniqueness constraint is what makes re-importing an export safe.';
COMMENT ON COLUMN kb_document.doc_date     IS 'Date the document is ABOUT (invoice date, email sent date) — never the filesystem timestamp.';
COMMENT ON COLUMN kb_document.metadata     IS 'Source-specific extras (gmail labels, tally voucher id, ...). Keeps the fixed columns small.';

-- ---------------------------------------------------------------------------
-- chunks: passages of a document, each independently embedded.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kb_chunk (
    id              BIGSERIAL PRIMARY KEY,
    document_id     BIGINT      NOT NULL REFERENCES kb_document(id) ON DELETE CASCADE,
    chunk_index     INTEGER     NOT NULL,           -- 0-based position within the document
    content         TEXT        NOT NULL,
    token_count     INTEGER,

    -- NOTE: the `embedding` column is added by migration 002, which requires
    -- pgvector. Keeping it out of this migration means the knowledge base
    -- installs and works (SQL + full-text) on any PostgreSQL, with semantic
    -- search as an upgrade rather than a hard dependency.
    embedding_model TEXT,                           -- e.g. 'text-embedding-3-small'; lets you spot rows needing re-embed

    tsv             TSVECTOR,
    UNIQUE (document_id, chunk_index)
);

COMMENT ON TABLE kb_chunk IS 'Passages of a document. Embeddings live here, not on kb_document, because one vector cannot represent a long mixed-topic file.';

-- ---------------------------------------------------------------------------
-- Full-text search vectors, kept current by trigger.
-- English config is the default; change it in a local migration for other
-- languages. Weights: A=subject/party (most selective), B=body.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION kb_document_tsv_update() RETURNS trigger AS $$
BEGIN
    NEW.tsv :=
        setweight(to_tsvector('english', coalesce(NEW.subject,  '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.party,    '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.filename, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.body_text,'')), 'C');
    RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS kb_document_tsv_trigger ON kb_document;
CREATE TRIGGER kb_document_tsv_trigger
    BEFORE INSERT OR UPDATE OF subject, party, filename, body_text
    ON kb_document FOR EACH ROW EXECUTE FUNCTION kb_document_tsv_update();

CREATE OR REPLACE FUNCTION kb_chunk_tsv_update() RETURNS trigger AS $$
BEGIN
    NEW.tsv := to_tsvector('english', coalesce(NEW.content, ''));
    RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS kb_chunk_tsv_trigger ON kb_chunk;
CREATE TRIGGER kb_chunk_tsv_trigger
    BEFORE INSERT OR UPDATE OF content
    ON kb_chunk FOR EACH ROW EXECUTE FUNCTION kb_chunk_tsv_update();

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS kb_document_tsv_idx      ON kb_document USING GIN (tsv);
CREATE INDEX IF NOT EXISTS kb_document_date_idx     ON kb_document (doc_date DESC);
CREATE INDEX IF NOT EXISTS kb_document_party_idx    ON kb_document USING GIN (party gin_trgm_ops);
CREATE INDEX IF NOT EXISTS kb_document_type_idx     ON kb_document (doc_type);
CREATE INDEX IF NOT EXISTS kb_document_thread_idx   ON kb_document (thread_id);
CREATE INDEX IF NOT EXISTS kb_document_metadata_idx ON kb_document USING GIN (metadata);

CREATE INDEX IF NOT EXISTS kb_chunk_tsv_idx         ON kb_chunk USING GIN (tsv);
CREATE INDEX IF NOT EXISTS kb_chunk_document_idx    ON kb_chunk (document_id);

-- Vector index lives in migration 002 (needs pgvector) and is created only
-- AFTER the first embedding run — IVFFlat on an empty table is useless.

-- ---------------------------------------------------------------------------
-- schema_version: so migrations are applied once and in order.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kb_schema_version (
    version     INTEGER     PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    description TEXT
);

INSERT INTO kb_schema_version (version, description)
VALUES (1, 'initial schema: sources, documents, chunks, FTS triggers, indexes')
ON CONFLICT (version) DO NOTHING;
