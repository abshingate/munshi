# ADR-0020: Document knowledge base on PostgreSQL + pgvector, ingested from user-run exports

- **Status:** accepted
- **Date:** 2026-07-28

## Context

Answering an ordinary finance question ("what did we pay this vendor across
FY22-23 to FY25-26, and was TDS deducted?") currently means hand-searching
four disconnected places: Gmail, Google Drive, the Tally company file, and a
folder of PDFs. A real session in July 2026 spent hours reconstructing four
years of one vendor's invoices from bank statements because no single
searchable record existed. The books, the correspondence that explains them,
and the documents that evidence them all live apart.

Constraints that shaped the decision:

- **The VM is stopped by default** (ADR-0001) and auto-stops when idle.
  Anything requiring an always-running service contradicts the cost model.
- **Every component must self-heal at boot** from the S3 assets bucket
  (ADR-0005). A knowledge base that needs manual re-setup after a restart is
  not deployable here.
- **The AI Accountant already exists** (ADR-0010): Node, pluggable LLM
  provider, Tally XML client, manual tool-use loop. A knowledge base should
  be another tool in that loop, not a second application.
- **Mail and Drive content cannot be fetched programmatically by the
  assistant.** Verified during the July 2026 session: the Gmail connector
  returns attachment *metadata* (filename, id, mimeType) with no content and
  no attachment-download tool; Drive was not connected at all. Any ingestion
  therefore starts from an export the user runs.
- Corpus scale for a small company is **tens of thousands of documents**,
  not millions — well under 1M embedding vectors.

## Options considered

- **Flat files + grep / filesystem search** — zero infrastructure and
  consistent with ADR-0012's "plain files a human can browse". Rejected as
  the primary index: it cannot answer relational questions (sum by vendor
  by financial year) or rank by relevance, which is most of the actual need.
- **SQLite + FTS5** — no server, no install, excellent full-text search,
  trivially backed up. Genuinely attractive and remains the fallback if
  Postgres proves heavy. Rejected because vector search support is an
  extension away from standard and concurrent access from the Node app plus
  ingestion jobs is awkward.
- **Qdrant (or another dedicated vector store)** — materially faster above
  ~10M vectors and richer filtered-vector search. Rejected: it solves a
  scale problem this deployment does not have, adds a *second* service to
  start, heal, and back up, and leaves relational queries homeless — the
  system would still need Postgres or SQLite beside it.
- **Managed cloud vector DB (Pinecone, Qdrant Cloud)** — no operational
  burden, but a recurring bill (~$25/mo entry pricing), and it moves private
  financial correspondence to a third party. Contradicts the project's
  keep-the-data-on-the-owner's-VM posture.
- **PostgreSQL + pgvector** — one service providing SQL, full-text search
  (`tsvector`), and vector similarity in the same query; `pg_dump` is one
  backup artifact; runs happily on the existing instance.

## Decision

A single **PostgreSQL instance on the VM with the `pgvector` extension**,
installed and converged by the repair loop like every other component
(ADR-0005), holding both the structured record and the searchable text.

- **Ingestion is from user-run exports**, not live API sync: Google Takeout
  (Mail as `.mbox` with attachments embedded, Drive as files) lands in the
  existing rclone-synced folder (ADR-0015) or is copied to the VM. A Python
  ingestion pipeline parses the mbox, extracts attachments, pulls text from
  PDF/DOCX/XLSX, and loads everything with its metadata.
- **Search is hybrid**: Postgres `tsvector` full-text for exact/keyword
  questions, pgvector cosine similarity for semantic ones, combined in a
  single SQL query with ordinary `WHERE` filters on date, sender, and vendor.
- **Embeddings are generated once per document version** via the same
  pluggable provider seam as ADR-0010 (`lib/llm.js`), so the embedding model
  is swappable and no vendor is hard-coded.
- **The knowledge base is exposed to the AI Accountant as tools**
  (`kb_search`, `kb_get_document`) in the existing tool-use loop — not as a
  separate chat application.
- **Documents on disk remain the source of truth** (ADR-0012). Postgres
  stores text, metadata, and vectors, plus a path back to the original file;
  it is an index, not a replacement. Losing the database costs a re-ingest,
  never a document.
- **`lib/docindex.js` (local JSON index of filed documents) is absorbed**,
  not duplicated: its filed-document metadata becomes rows in the same
  schema, so there is one index rather than two with different answers. It
  remains as the zero-dependency fallback path while Postgres is optional.

## Consequences

- **One service, one backup.** `pg_dump` joins the nightly snapshot; a
  restore is one command. No second store to coordinate or heal.
- **Relational and semantic questions share one query.** "Every ARTH payment
  after April 2022 ranked by similarity to 'audit fee'" is one statement
  rather than an application-side join across two systems.
- **Cost is effectively zero beyond storage.** Postgres and pgvector are
  free; embedding a small-company corpus once is a few hundred rupees of API
  usage at 2026 rates, or free with a local model. S3 Deep Archive for the
  raw export zips is ~₹160/TB/month if the user wants offsite retention.
- **Ingestion is a batch job the user triggers**, so the knowledge base is
  as fresh as the last export. This is a deliberate limitation: live Gmail
  sync would need OAuth, a running poller, and an always-on VM — all three
  contradict existing ADRs. Re-export cadence is the user's choice.
- **Scale ceiling accepted.** Above roughly 10M vectors pgvector's recall or
  latency may disappoint; that is far beyond a small company's corpus and the
  migration to a dedicated store is a known, bounded job if it ever arrives.
- **Privacy scope is the user's to set.** The pipeline takes whatever export
  it is given; a filtered export (by label or date) is the recommended
  default so a personal mailbox is not copied onto a shared finance machine.
  This must be stated plainly in the user-facing guide.
- Adding a source (WhatsApp export, another mail provider) is one parser
  writing into the same schema — deliberately a narrow seam, like ADR-0010's
  provider and tool seams.
