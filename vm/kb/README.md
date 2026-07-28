# Knowledge base

A searchable index of your company's documents and correspondence — emails,
attachments, invoices, statements, filings — so a question like *"what did we
pay this vendor across the last four years, and did we deduct tax?"* is one
query instead of an afternoon of hunting.

Design and rationale: **[ADR-0020](../../docs/decisions/0020-knowledge-base-postgres-pgvector.md)**.

## What it is

One PostgreSQL database on the VM with the `pgvector` extension, holding three
kinds of search in the same place:

| Question | Answered by |
|---|---|
| "every invoice from ARTH after April 2022" | SQL `WHERE` |
| "emails mentioning section 194I" | full-text search (`tsvector`) |
| "what did we agree about audit fees?" | vector similarity (`pgvector`) |

They combine: you can filter by date and party *and* rank by meaning in a
single statement. That combination is the whole reason for choosing Postgres
over a dedicated vector store — see the ADR.

**Your files on disk stay the source of truth.** This database is an index.
Every row carries `source_path` back to the original. Losing the database
costs a re-ingest; it never costs a document.

## Requirements

- **PostgreSQL 14+** — installed automatically by the repair loop on the VM
- **Python 3.9+** with `psycopg[binary] pypdf python-docx openpyxl beautifulsoup4`
- **pgvector** *(optional)* — enables semantic search
- **An embedding provider** *(optional)* — OpenAI-compatible, or none

### On pgvector being optional

Everything works without it: SQL filters, full-text ranking, snippets,
aggregates. Only *semantic* search (find by meaning rather than words) needs
it. Migration 001 creates the whole schema without pgvector; migration 002
adds the embedding column once you have it.

**Verified on Windows:** the PostgreSQL 18 Chocolatey package does **not**
bundle pgvector. On that platform, either use a build that includes it, run
Postgres in the `pgvector/pgvector` Docker image, or compile the extension.
The knowledge base installs and runs regardless — `ingest.py --stats` will
tell you which mode you are in.

## Setup

```bash
createdb munshi_kb
psql -d munshi_kb -f migrations/001_initial_schema.sql
```

Migrations are numbered and idempotent. `kb_schema_version` records what has
been applied; re-running is safe.

## Getting your data in

The pipeline ingests from **exports you run**, not live API access. This is
deliberate (ADR-0020): live mail sync would need OAuth, a running poller, and
an always-on VM, all of which contradict this project's stopped-by-default
cost model.

### Google Workspace / Gmail + Drive

1. Go to [takeout.google.com](https://takeout.google.com)
2. Select **Mail** (exports as `.mbox` with attachments embedded) and
   **Drive** (exports the actual files)
3. **Scope it deliberately.** Gmail lets you export selected labels only. A
   business-only export keeps a personal mailbox off a shared finance
   machine — recommended default.
4. Choose ~2 GB splits; the export takes hours to days depending on volume
5. Download and unzip somewhere the VM can read

### Other sources

Any directory of files works:

```bash
python ingest.py --source filesystem --path /path/to/documents
```

Adding a new source type (another mail provider, a WhatsApp export) means
writing one parser that populates the same schema — a deliberately narrow
seam.

## Ingesting

```bash
python ingest.py --source gmail-takeout --path ~/Takeout/Mail/business.mbox
python ingest.py --source drive-takeout --path ~/Takeout/Drive
python ingest.py --embed                 # generate embeddings (optional)
```

Ingestion is **idempotent**: documents are keyed by SHA-256 of their bytes,
so re-running an import never duplicates. Re-export and re-run whenever you
want the index refreshed — the knowledge base is as fresh as your last export.

After the first embedding run, create the vector index (pointless on an empty
table, which is why it isn't in the migration):

```sql
CREATE INDEX kb_chunk_embedding_idx ON kb_chunk
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
ANALYZE kb_chunk;
```

Rule of thumb for `lists`: about `rows / 1000`, minimum 10.

## Searching

`search.py` is the command-line front end; it prints plain text for humans and
JSON (`--json`) for tools.

```bash
python search.py "audit fee"                       # full-text, ranked, with snippets
python search.py "rent" --party palkar --since 2026-04-01
python search.py --type invoice --list             # filter only, no snippets
python search.py --doc 171                         # one document in full
python search.py --sql "SELECT party, count(*) FROM kb_document GROUP BY 1"
```

Filters compose with search, which is the whole point of the design: you can
narrow by party, type and date *and* rank by relevance in one query.

## Querying directly

Keyword, filtered:

```sql
SELECT doc_date, party, subject, source_path
FROM kb_document
WHERE tsv @@ plainto_tsquery('english', 'audit fee')
  AND doc_date >= '2022-04-01'
ORDER BY ts_rank(tsv, plainto_tsquery('english', 'audit fee')) DESC
LIMIT 20;
```

Semantic, filtered — the pattern a dedicated vector store cannot do alone:

```sql
SELECT d.doc_date, d.party, c.content
FROM kb_chunk c
JOIN kb_document d ON d.id = c.document_id
WHERE d.party ILIKE '%arth%'          -- ordinary SQL filter
  AND d.doc_date >= '2022-04-01'
ORDER BY c.embedding <=> :query_vector -- cosine distance
LIMIT 10;
```

Aggregate — because it is a real database:

```sql
SELECT party,
       date_trunc('year', doc_date) AS yr,
       sum(amount) AS total
FROM kb_document
WHERE doc_type = 'invoice'
GROUP BY party, yr
ORDER BY yr DESC, total DESC;
```

## Customising for your company

Nothing here is jurisdiction- or Tally-specific.

- **`doc_type` and `party` are free text.** Use your own vocabulary; no
  enum to fight.
- **`metadata` is JSONB.** Put source-specific fields there rather than
  altering the schema.
- **Language:** the full-text triggers use the `english` configuration.
  Change it in a new migration for other languages.
- **Embedding model:** `kb_chunk.embedding` is `VECTOR(1536)`. A different
  model with different dimensions needs a new migration and a re-embed —
  pgvector cannot mix dimensions in one column. `embedding_model` records
  what produced each row so you can find stale ones.
- **Currency** defaults to `INR`; change the column default.

## Backup

One artifact, alongside the nightly snapshot:

```bash
pg_dump munshi_kb > munshi_kb.sql
```

Being an index, it is also fully rebuildable from your exports — so a backup
is convenience, not a dependency.

## Privacy

Ingest only what you need. A finance knowledge base wants invoices,
statements, filings, and vendor correspondence — not a personal mailbox.
Gmail's label-filtered export exists for exactly this; use it. The database
holds extracted text in plain form, so it deserves the same care as the
documents themselves.
