# Tax Knowledge Platform — acquisition and integration plan

Status: **DEFERRED (2026-07-28).** Analysis retained; not being built.
Companion to [ADR-0020](decisions/0020-knowledge-base-postgres-pgvector.md)
(document knowledge base, built and running).

## Why deferred

The decision was to focus the knowledge base on **company data** — the
documents, correspondence and books that no public corpus contains — and to
answer tax-law questions by verifying against primary sources at the time of
asking, rather than maintaining a private copy of Indian tax law.

The reasoning:

- **The corpus would need permanent maintenance.** Every Finance Act, every
  CBDT circular, forever. A stale tax corpus is worse than none, because it
  cites superseded law with the same confidence as current law.
- **Verification at question-time already works.** In practice, the tax
  questions that arise (thresholds, section codes, GST treatment) are
  answered by reading the department's own material at the moment of the
  question — and the one error made during a full day of tax work came from
  reasoning by pattern *instead of* checking a source, which a corpus would
  not have prevented.
- **The real difficulty is company-specific.** Reconstructing four years of
  a vendor's invoices, reconciling bank against books, finding the email that
  explains a decision — none of that is in any public dataset.

**What was kept instead**, as small, testable artefacts rather than a corpus:

1. **Rules tables** — the handful of rates, thresholds and due dates actually
   used, encoded with their basis (the per-month vs per-year distinction that
   caused a real error) and covered by tests. Deterministic computation, not
   retrieval.
2. **A curated guide** kept current for the sections this company uses.
3. **Decision records with reasoning** — worth more than case law here,
   because they record what happened in *this* business and why.

Revisit if: the assistant serves multiple companies, or questions routinely
need statutory text this approach cannot reach.

The feasibility analysis below is retained because it remains accurate and
would be the starting point if the decision is reversed.

The goal: an assistant that answers Indian tax questions **with citations to
primary law, correct for the year asked about**, and that says "I don't know"
rather than guessing.

---

## The governing principle

> A tax knowledge base that *looks* complete but has silent gaps is more
> dangerous than a small one that knows its own limits.

A wrong citation delivered confidently is worse than no answer: it gets acted
on. Every design choice below follows from that.

Three rules fall out of it:

1. **Never synthesise law.** If a section's text was not successfully
   retrieved, the assistant must refuse, not paraphrase from memory.
2. **Every claim carries a source and a date range.** "194J is 10%" is wrong
   without "for FY 2024-25, per s.194J as amended by Finance Act 2020".
3. **Coverage must be measurable.** We must be able to answer "what fraction
   of sections do we actually hold?" — otherwise nobody knows what the
   assistant doesn't know.

---

## Honest feasibility assessment

The 24-layer plan is directionally right. Some layers are straightforward,
some are hard, and two are traps. Assessed before building rather than after.

| Layer | Feasibility | Reality |
|---|---|---|
| 1. Acts, Rules, Finance Acts | **High** | Published as PDF/HTML on incometaxindia.gov.in. No API; needs a polite crawler. Bounded and knowable. |
| 2. Notifications, Circulars | **High** | Listed by year on the department site. Thousands of documents; volume, not difficulty. |
| 3. FAQs | **Medium** | Scattered across portals, inconsistent formats, undated. Useful but never authoritative — label as *guidance*. |
| 4. Forms | **High** | Downloadable, plus JSON schemas and validation rules for ITR utilities. The schemas are unusually good structured data. |
| 5. Tax rates | **Medium** | No official machine-readable table exists. Must be **hand-built from Finance Acts and verified**. Highest-value, highest-risk layer. |
| 6. TDS sections | **Medium** | Same: structure it ourselves from the Act + Finance Acts. |
| 7. **Case law** | **Low–Medium** | The hard one. See below. |
| 8. Advance rulings | **Medium** | AAR/BAR published but poorly indexed. |
| 9. Tax audit | **High** | Subset of layers 1–4. |
| 10–14. GST, Companies Act, MCA, RBI, SEBI | **Medium** | Each is a project of comparable size to income tax. **Scope creep risk.** |
| 15–16. Ind AS, ICAI | **Low** | Much ICAI material is **copyrighted and paywalled**. Cannot be redistributed in an open-source repo. |
| 17. Portal documentation | **High** | Straightforward downloads. |
| 18–19. Due dates, penalties | **Medium** | Hand-built structured data; verify against the Act. |
| 20–22. Examples, calculators, checklists | **N/A** | We author these; they are outputs, not downloads. |
| 23. Historical versions | **High effort, essential** | See below — this is the layer most projects skip and most regret. |
| 24. Knowledge graph | **Medium** | Emerges from good metadata; not a separate acquisition task. |

### Case law: the honest position

Rated ⭐⭐⭐⭐⭐ in the plan, and correctly so — but it is the layer most likely
to be done badly.

- **Volume:** Indian Kanoon indexes 30M+ judgments. Income-tax matters alone
  run to hundreds of thousands across SC, 25 High Courts and ITAT benches.
- **Access:** Indian Kanoon has a **paid API** (per-call). eCourts publishes
  High Court judgments in bulk (JSON/Parquet/tar, 1950–2025). ITAT publishes
  its own orders. There is no single free bulk source for everything.
- **Licensing:** judgments are public record, but *databases* of them may be
  licensed. **Scraping Indian Kanoon rather than using its API breaches its
  terms.** For an open-source project this must be respected, not skirted.
- **The real difficulty is not acquisition, it is precedent status.** A
  judgment that has been overruled, distinguished, or is under appeal is
  actively harmful if cited as good law. Citator data — which cases are still
  good — is the expensive part, and no free source provides it reliably.

**Recommendation:** phase case law *last*, start with Supreme Court +
jurisdictional High Court only, and mark every judgment with an explicit
"precedent status unverified" flag unless we have citator data. An assistant
that cites an overruled case with confidence is worse than one that cites
none.

### Copyright: what we cannot redistribute

Statutes, rules, notifications, circulars and judgments are government works
and freely usable. **ICAI guidance notes, Ind AS bare texts, and commercial
commentary are copyrighted.** They may be readable by a licensed user but
cannot be committed to a public repo or shipped in a container image.

Design consequence: the pipeline must separate **redistributable** sources
(committed, shared) from **local-only** sources (a user's own licensed
copies, ingested on their machine, never in the repo). This is a schema flag,
not an afterthought.

### Scope creep

Layers 10–14 (GST, Companies Act, MCA, RBI, SEBI) are each comparable in size
to income tax. Attempting all of them at once produces six half-built corpora
and an assistant that is unreliable in every domain.

**Recommendation:** build income tax + TDS to a high standard, prove the
architecture and the evaluation suite, then add domains one at a time.

---

## What makes this different from a document dump

### Chunk by legal hierarchy, never by character count

Fixed-size chunking destroys law. A proviso severed from its section reverses
meaning; an Explanation orphaned from its subsection is unintelligible.

```
Act → Chapter → Section → Sub-section → Clause → Proviso → Explanation
```

Each chunk carries its full ancestry, so a retrieved proviso arrives with the
section it qualifies.

### Temporal validity is not optional

Every provision needs `effective_from` and `effective_to`. "What is the 194J
rate?" has different correct answers for FY 2019-20 and FY 2024-25, and an
assistant that cannot distinguish them is unusable for compliance work — the
questions are almost always about a past year.

This is what makes the *amendment chain* essential: each Finance Act edit
must be recorded as a version, not an overwrite.

### The LLM must not compute statutory values

Deterministic engine computes; model explains and cites. Tax arithmetic —
slabs, surcharge, marginal relief, interest under 234A/B/C, TDS thresholds —
is rule-following, exactly what LLMs do unreliably and code does perfectly.

The July 2026 session that motivated this makes the point: the ₹50,000
**per month** vs **per year** threshold under 194I was the error that led to
tax being deducted when none was due. A rules table gets that right every
time; a language model may not.

### Evaluation before expansion

A test suite of verified scenarios with known answers, run on every ingest.
Without it there is no way to know whether adding a corpus improved or
degraded accuracy. Seed it from real resolved cases — the TDS work in this
repo supplies a dozen immediately.

---

## Proposed phasing

Each phase ends with something usable. No phase depends on a later one.

**Phase 1 — Foundation (income tax primary law)**
Acts 1961 + 2025, Rules 1962 + 2026, Finance Acts 2005–2026, with the
amendment chain and section-level temporal validity. Deliverable: cite any
section as it stood in any year.

**Phase 2 — Administrative material**
Notifications, circulars, instructions, press releases; linked to the
sections they affect. Deliverable: "what has CBDT said about 194J?"

**Phase 3 — Structured rules**
Tax rates, TDS sections, thresholds, due dates, penalties as *typed tables*
feeding the deterministic engine. Hand-built, verified against primary law,
covered by tests. Deliverable: correct computation with citations.

**Phase 4 — Forms and portal documentation**
Forms, JSON schemas, validation rules, utilities.

**Phase 5 — Evaluation suite**
Several hundred scenarios with verified answers. Runs in CI.

**Phase 6 — Case law (bounded)**
Supreme Court + one jurisdictional High Court, income-tax matters, with
explicit precedent-status flags.

**Phase 7+ — Adjacent domains, one at a time**
GST first (most entangled with income tax), then Companies Act.

---

## Architecture

Largely as proposed, with two deliberate simplifications:

| Component | Choice | Why |
|---|---|---|
| Raw documents | Filesystem + S3 archive | Source of truth stays as files (ADR-0012) |
| Structured store | **PostgreSQL** | Already built (ADR-0020); sections, rates, dates, penalties |
| Full-text | **Postgres FTS** | Already working; no second service |
| Vectors | **pgvector** | Same database, filters compose with similarity |
| Graph | **Postgres relations, not Neo4j** | The graph is ~6 relation types over ~50k nodes. A separate graph DB is unjustified at this scale and adds a service to run, heal and back up. Revisit if traversals get genuinely deep. |
| Search | **Postgres hybrid**, not OpenSearch | Same reasoning: one service. Revisit above ~10M chunks. |
| Rule engine | Python, table-driven, unit-tested | Statutory values are never LLM-generated |
| Assistant | Existing AI Accountant tool loop (ADR-0010) | `kb_search`, `kb_cite`, `tax_compute` as tools |

The deviations from the proposal (no Neo4j, no OpenSearch) follow ADR-0020's
reasoning: this deployment is a stopped-by-default single VM, where each
additional service is one more thing to start, converge and back up. Both
remain sensible upgrades at a scale we have not reached.

---

## Schema sketch

Extends the existing `kb_*` tables rather than replacing them.

```sql
-- A provision as it stood during a specific period.
CREATE TABLE tax_provision (
    id              BIGSERIAL PRIMARY KEY,
    corpus          TEXT NOT NULL,        -- 'income-tax-act-1961' | 'income-tax-act-2025' | ...
    section         TEXT NOT NULL,        -- '194J'
    subsection      TEXT,                 -- '(1)(a)'
    hierarchy       TEXT[],               -- ancestry: chapter → section → clause
    heading         TEXT,
    text            TEXT NOT NULL,
    effective_from  DATE NOT NULL,
    effective_to    DATE,                 -- NULL = still in force
    amended_by      TEXT,                 -- 'Finance Act 2020, s.78'
    source_document BIGINT REFERENCES kb_document(id),
    UNIQUE (corpus, section, subsection, effective_from)
);

-- Typed rules the deterministic engine reads. NEVER free text.
CREATE TABLE tax_rule (
    id              BIGSERIAL PRIMARY KEY,
    rule_type       TEXT NOT NULL,        -- 'tds_rate' | 'slab' | 'threshold' | 'due_date' | 'penalty'
    section         TEXT,
    applies_from    DATE NOT NULL,
    applies_to      DATE,
    params          JSONB NOT NULL,       -- {rate: 10, threshold: 50000, basis: 'per_month'}
    authority       BIGINT REFERENCES tax_provision(id),   -- MUST cite a provision
    verified_by     TEXT,
    verified_on     DATE
);

-- Relations: the knowledge graph, as ordinary rows.
CREATE TABLE tax_relation (
    from_type TEXT, from_id BIGINT,
    to_type   TEXT, to_id   BIGINT,
    relation  TEXT,   -- 'amends' | 'clarifies' | 'interprets' | 'prescribes_form' | 'overrules'
    PRIMARY KEY (from_type, from_id, to_type, to_id, relation)
);
```

`tax_rule.authority` being NOT NULL in practice is the mechanism that stops
invented rates: a rule with no cited provision cannot be trusted, and the
loader rejects it.

---

## Coverage and honesty instrumentation

Non-negotiable, and the part most projects omit:

- **Coverage report:** sections held vs sections known to exist, per corpus
  per year. Published, not hidden.
- **Staleness:** last successful crawl per source; flag anything overdue.
- **Refusal path:** when retrieval returns nothing above a confidence floor,
  the assistant says so and points to the source it *would* have used.
- **Citation required:** answers about law must carry provision ids. An
  uncited legal claim is a bug, not a style issue.

---

## Immediate next step

Phase 1, narrowed to something verifiable: **the TDS sections of both Acts,
with the full amendment chain from Finance Acts 2005–2026.**

Why this slice: it is the domain this repo already works in daily, the
existing register supplies real test cases, and it is small enough to verify
by hand — which means we can prove the temporal-validity model works before
scaling it to the whole Act.

Success criterion: the assistant correctly answers "what was the 194J
threshold in FY 2019-20 versus FY 2024-25, and what changed?" with citations
to the specific Finance Act amendments — and refuses to answer where we hold
nothing.
