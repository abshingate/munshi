-- Munshi knowledge base — semantic search (ADR-0020)
--
-- OPTIONAL migration. Requires the `vector` extension (pgvector).
-- Migration 001 deliberately leaves this out so the knowledge base installs
-- and works on any PostgreSQL; semantic search is an upgrade, not a
-- prerequisite. SQL filters and full-text search work without it.
--
-- Installing pgvector:
--   * Linux/macOS  : available in most package repos, or build from source
--                    (https://github.com/pgvector/pgvector)
--   * Windows      : not bundled with every packaged build. Either use a
--                    distribution that includes it, or build with MSVC.
--   * Docker       : the `pgvector/pgvector` images include it.
--
-- Re-running is safe.

-- Run inside a transaction so a missing extension rolls the WHOLE migration
-- back, including the schema_version row. Without this, psql continues after
-- the error and records a version that was never actually applied.
BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

-- Dimension note: 1536 fits OpenAI text-embedding-3-small and many others.
-- A model with different dimensions needs a NEW migration and a re-embed —
-- pgvector cannot mix dimensions in one column. `embedding_model` (added in
-- 001) records what produced each row so stale vectors are findable.
ALTER TABLE kb_chunk ADD COLUMN IF NOT EXISTS embedding VECTOR(1536);

COMMENT ON COLUMN kb_chunk.embedding IS
    'Cosine-distance vector for semantic search. NULL until ingest.py --embed runs.';

-- The IVFFlat index is intentionally NOT created here: it must be built on a
-- populated table or it produces poor recall. Create it after your first
-- embedding run, sizing `lists` at roughly rows/1000 (minimum 10):
--
--   CREATE INDEX kb_chunk_embedding_idx ON kb_chunk
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
--   ANALYZE kb_chunk;

INSERT INTO kb_schema_version (version, description)
VALUES (2, 'pgvector embedding column on kb_chunk (optional; semantic search)')
ON CONFLICT (version) DO NOTHING;

COMMIT;
