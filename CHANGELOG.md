# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [1.20.0] - 2026-07-29

### Added

- **Coordinate-aware statement extraction** (`vm/rules/pdf_table.py`): reads
  bank PDFs whose text layer is fragments rather than lines, by grouping text
  by (x, y) position and learning the column geometry from the statement
  itself rather than hard-coding it. On the statement it was built against it
  extracts 240 transactions where line parsing extracted zero.
  - `cross_check()` verifies that transactions **known** to be in a period
    were actually extracted.
  - `sanity_check()` tests balance continuity, date ordering and completeness
    of dates.

### Notes

- **The extractor is ASSISTIVE, not authoritative, and says so in its
  docstring.** Cross-checking against known transactions showed it missed a
  ₹1,47,500 payment and a ₹5,50,000 payment, and found 9 of 12 monthly
  challans — while every internal indicator looked healthy. Two causes: the
  statement interleaves two accounts so a single balance chain does not
  apply, and some rows split date and amount differently from the anchor
  heuristic.
- The general lesson (L009): **balance continuity proves internal
  consistency, not completeness.** A self-consistent extraction can still be
  missing a third of the statement. Only checking for transactions you
  already know exist catches that. Coverage is never marked "held" on this
  extractor's output alone.

## [1.19.0] - 2026-07-29

### Added

- **Advisor cross-check** (`vm/rules/crosscheck.py`, `advice.json`): records
  professional advice and flags where it disagrees with the encoded rules.
  **It does not decide who is right.** An adviser may know something the rule
  set does not; the output says so explicitly. What it prevents is a
  disagreement passing unnoticed.
  - Two reasons to record advice: a conflict becomes a decision made
    knowingly rather than by default, and reliance on advice that later
    proves wrong is provable — which matters in penalty proceedings.
  - Advice with no machine-checkable claim is kept for the audit trail and
    explicitly *not* judged.
  - Exits non-zero when a conflict stands, so it can gate a workflow.
  - Seeded with the real case: an adviser's tax team computed ₹12,500 of TDS
    at 09:58, then withdrew it at 11:11 — 73 minutes later — on the ground
    that the company had accumulated losses. Losses bear on the s.40(a)(ia)
    disallowance, not on the deductor's liability under s.201. The register
    records both positions, and the checker confirms the first agrees with
    the rules and the second conflicts.

### Notes

- Completes the six phases in `docs/compliance-safety-net.md` except phase 4
  (assisted data entry, ADR-0021), which is deliberately unbuilt pending
  approval — it types into government portals and its human-approval gates
  are security properties.

## [1.18.0] - 2026-07-29

### Added

- **Evidence completeness** (`vm/rules/evidence.py`): answers the question an
  audit actually asks — *what is missing?* Documents were already searchable
  and filed entries already carried a marker back to their voucher; both
  answer "find the document for this entry". This answers the reverse.
  - `EVIDENCE_RULES` encodes what each kind of transaction needs: a vendor
    payment needs an invoice, a tax payment needs a challan, bank interest
    and internal transfers need nothing. Transactions needing no document are
    **excluded** from the percentage rather than counted as failures —
    counting bank charges as "missing evidence" would bury the real gaps.
  - `--report` gives completeness by document type; `--missing --min N`
    lists what to go and find, largest first.
  - Evidence matching is deliberately conservative (amount within ₹1 **and**
    date within 15 days, or a distinctive reference token). A loose match
    that reports "evidence found" when it has not been is worse than
    reporting a gap, because it closes the question wrongly.

### Fixed

- **The statement loader reported "no transactions" for a statement full of
  them.** A full-year PDF extracts as fragmented text with dates and amounts
  on separate lines, which the line-based parser cannot match — and it
  reported zero and moved on. In use this would have been worse than a crash:
  coverage would show the year as loaded, evidence completeness would show
  100%, and a year of activity would be invisible while every indicator said
  fine. `diagnose_text()` now names the actual cause and the loader refuses
  to mark coverage "held" when nothing parsed.

## [1.17.0] - 2026-07-29

### Added

- **Continuous reconciliation** (`vm/rules/reconcile.py`): bank statements
  loaded into `bank_transaction`, exceptions that persist between runs, and
  coverage tracked per financial year. The existing matcher
  (`vm/app/lib/recon.js`) is not replaced — its four-pass matching is sound;
  what was missing was continuity, so nothing accumulated and nothing was
  watched across periods.
  - Idempotent on a row hash that includes the description, so two identical
    amounts on one day stay distinct rather than silently collapsing.
  - `--exceptions` lists bank lines with no matching voucher: money moved and
    the books do not know. That list is the product.
  - `--status` reports evidence coverage per year, marking years that cannot
    be verified at all.

### Fixed

- **Statement parser invented transactions from page furniture.** A printed
  timestamp ("Date And Time : 09/03/2026 12.44 PM") became a ₹12.44 line and
  a "Lien Balance: 0.00" footer became a zero-value line, because the only
  test applied was "contains a date and a number". Fixed with a noise filter
  whose every pattern comes from an observed false positive, plus a rule that
  at least one amount must exceed zero. On the real statement that exposed
  it: 6 parsed rows became 4, all genuine.

### Notes

- Failing to read a transaction is recoverable by re-reading; **inventing one
  is not**, because nothing downstream can distinguish it from a real line.
  The parser is deliberately strict in that direction and
  `vm/rules/test_reconcile.py` holds it there.

## [1.16.0] - 2026-07-29

### Added

- **Compliance monitor** (`vm/rules/monitor.py`): deadlines and thresholds,
  answered through the rules engine so it holds no tax knowledge of its own.
  - Deadline tracking across the salary schedule, undeposited vendor TDS and
    quarterly returns, with overdue items separated from approaching ones.
  - **Cumulative threshold monitoring per vendor per section**, flagging
    `breached-undeducted` and `approaching` (80%) — the control that was
    missing while a vendor was paid gross for four consecutive years.
  - `--check-payment VENDOR AMOUNT RULE` answers *"what happens if I pay
    this?"* **before** the money moves, returning the net amount to pay and
    any catch-up on earlier untaxed payments. Checking after payment is how
    gross payments accumulate.
  - Alerts for a quarter already carrying an acknowledgement are suppressed:
    an alert that fires for completed work trains the operator to ignore
    alerts.
- **Lessons register** (`vm/rules/lessons.json`): every mistake, its root
  cause, and the concrete safeguard that now prevents it. Six entries so far,
  each naming an executable control.
- **Tests** (`vm/rules/test_rules.py`, 26 cases): engine correctness, rule-set
  integrity (every rule cites an authority and is effective-dated), and
  **process integrity** — a test asserts that no lesson's safeguard is a
  vague intention. Verified by negative test: "Be more careful next time" is
  rejected with a clear failure.
- Health check gained a rules-engine test; CI runs the rules and lessons
  tests on every push.

### Notes

- The lessons register exists because a mistake that produces only an apology
  will recur, while one that produces a test will not. The
  `safeguards_are_concrete_not_intentions` test is what gives "we learned
  from it" a definition: something now fails if it happens again.

## [1.15.0] - 2026-07-29

### Added

- **TDS rules engine** (`vm/rules/`): statutory values are computed by
  table-driven code, never derived by the language model. Rates, thresholds,
  due dates, interest and penalties live in `tds-in.json`; `tds_engine.py`
  applies them.
  - **Every rule carries its authority and its effective dates.** A rule with
    no citation fails CI. A question about a date outside a rule's period is
    refused rather than answered with the current rule — compliance questions
    are almost always about a past period.
  - **Threshold basis is explicit** (`per_month`, `per_year_per_vendor`,
    `per_invoice_or_annual_aggregate`, `no_threshold`), because conflating
    them is exactly how a real over-deduction happened: s.194I rent is
    ₹50,000 **per month**, so ₹30,000/month needs no TDS despite being
    ₹3,60,000 a year.
  - Handles the 194C dual test, aggregate-crossing catch-up on earlier
    untaxed payments, the s.194Q excess-only basis, and refuses s.195
    outright as requiring a human.
  - Interest counts a part month as a full month; the s.234E fee is capped at
    the statement's TDS.
  - 15 rules, all citing the Income-tax Act 2025 section and the superseded
    1961 section, with the new-Act payment codes (1009 rent, 1027
    professional fees, and the rest).
- CI job `rules-engine`: runs the self-test, validates the rule set parses,
  and fails if any rule lacks an authority citation.

### Notes

- The self-test cases are drawn from real filed work — the Palkar rent, the
  ARTH audit fee, the Dipti Thite threshold crossing, the interest on the
  FY25-26 ARTH default — not from invented examples. Statutory arithmetic
  must not regress silently.

## [1.14.0] - 2026-07-28

### Added

- **Company history layer** (`vm/kb/migrations/003_company_history.sql`):
  extends the knowledge base from "find the document" to "what happened in
  this business, and do the books agree with the bank?".
  - `bank_transaction` — evidence: what the bank says moved, raw narration
    preserved, idempotent on a row hash.
  - `tally_voucher` / `tally_entry` / `tally_ledger` — assertion: what the
    books claim.
  - `recon_match` — where the two meet **or fail to**. A bank-only row is a
    missing book entry; a books-only row is an accrual or an error. The
    exceptions are the product, not a by-product.
  - `finding` — durable record of verification results with evidence and
    status.
  - `coverage` — what evidence exists per financial year. Queried *before*
    answering, so the assistant can say "no data for FY 2016-17" rather than
    answering confidently from nothing.
  - `fin_year` — explicit financial-year calendar (the boundary is
    jurisdiction-specific and every query needs it).
  - Views `v_unmatched_bank` (money moved with no voucher) and
    `v_party_activity` (everything known about a counterparty).

### Notes

- Documents answer "find X"; transactions answer "how much, when, and does
  it reconcile?". Both live in one database precisely so they can be joined —
  the reason for choosing PostgreSQL over a document or vector store alone
  (ADR-0020).

## [1.13.0] - 2026-07-28

### Added

- **Document knowledge base** (`vm/kb/`, see
  [ADR-0020](docs/decisions/0020-knowledge-base-postgres-pgvector.md)): a
  searchable index of a company's documents and correspondence, so questions
  like "what did we pay this vendor over four years, and was tax deducted?"
  are one query instead of an afternoon across Gmail, Drive, Tally and a
  folder of PDFs. PostgreSQL holds structured columns, full-text search and
  (optionally) vector embeddings in one place, so filters and relevance
  ranking compose in a single statement.
  - `migrations/` — numbered, idempotent SQL tracked in `kb_schema_version`.
  - `ingest.py` — parses Google Takeout mbox (messages **and** attachments),
    any directory of files; extracts text from PDF/DOCX/XLSX/HTML; chunks
    with overlap; idempotent on SHA-256 of file bytes, so re-importing an
    export never duplicates.
  - `search.py` — full-text ranking with snippets, composable filters
    (party, type, date range), single-document view, and read-only
    aggregate SQL. Plain-text output for humans, `--json` for tools.
  - `vm/kb-setup.ps1` — provisions Python, PostgreSQL, the schema and data
    folders through the existing repair loop, so a new deployment gets the
    knowledge base at first boot and self-heals at every boot thereafter
    (ADR-0005), like every other component.
- Documents on disk remain the source of truth (ADR-0012): every row keeps
  `source_path` back to the original file, and the index is rebuildable from
  the exports at any time.

### Notes

- **pgvector is optional.** Migration 001 creates the entire schema without
  it; migration 002 adds the embedding column where the extension exists.
  SQL filters, full-text search and aggregates all work either way — only
  semantic search requires it. Verified during rollout: the PostgreSQL 18
  Chocolatey package on Windows Server does **not** bundle pgvector, and the
  knowledge base installs and runs correctly regardless.
- Ingestion reads exports the user runs (Google Takeout), not live APIs:
  live mail sync would require OAuth, a running poller and an always-on VM,
  each contradicting the stopped-by-default cost model (ADR-0001).

### Fixed

- Document classification ignored filenames containing `_` or `-`: `re`
  treats them as word characters, so `\bchallan\b` did not match
  `2026-05-07_challan.pdf` — precisely the naming convention ADR-0012
  prescribes. Scanned documents, which often yield no extractable text, were
  therefore left unclassified and invisible to type filters. Separators are
  now normalised before matching and the filename is searched before the
  body. Measured on a real corpus of 291 documents: unclassified fell from
  165 to 131, invoices rose from 85 to 118.

### Testing

- `vm/kb/test_ingest.py`: 24 unit tests over the ingestion logic most likely
  to corrupt the index silently — control-character stripping, chunk
  boundaries and content preservation, hash idempotency, amount extraction,
  document classification. Runs with no database and no driver, so it works
  in CI and on a contributor's machine.
- `ingest.py` and `search.py` no longer exit at import when `psycopg` is
  absent; the driver is required only when a connection is actually opened.
- CI job `knowledge-base` runs the tests and byte-compiles the pipeline.
- `vm/health-check.ps1` gained seven knowledge-base checks (PostgreSQL
  installed, database responds, schema present, search works end-to-end,
  index populated, semantic search available, Python pipeline importable).
  Verified by negative test: stopping PostgreSQL produces three FAILs with
  actionable hints and exit code 1; restarting restores all PASS.

## [1.12.0] - 2026-07-27

### Added

- **Financial-statements generator** (`vm/app/lib/fsgen.js`, see
  `docs/fs-generator.md`): produces complete Schedule III annual financial
  statements — Balance Sheet, P&L, all notes, Companies Act depreciation
  schedule, EPS, key ratios — directly from a ledger-level Tally trial
  balance and a JSON company config (`vm/app/fs-config/example-config.json`).
  Exact paise arithmetic until the presentation pass; generation is refused
  while any validation fails (TB balance, unmapped ledgers, BS balance in
  paise, depreciation ties, reserves continuity, independent P&L recompute,
  related-party reconciliation); ₹'000 rounding-footing artefacts are
  reported, never hidden. Validated by regenerating an audited year's signed
  statements: 95/96 values exact, the one difference being a manual
  adjustment in the auditor's workbook that the books did not contain.

## [1.11.0] - 2026-07-27

### Added

- **Default users out of the box** (`create_default_users`, on by default):
  every deployment converges `Accountant` (entry) and `Auditor` (review) as
  fenced non-admin RDP users at every boot — recreated if deleted, passwords
  generated by Terraform and enforced; `scripts/get-password.sh` (button 2)
  now prints Administrator + both role passwords for sharing.
- **Optional internet-reachable RDP** (`rdp_open_to_internet`, default
  `false`): lets additional users connect from any network without allowlist
  upkeep — a documented trade-off; browser desktop, AI app and SSH always stay
  allowlist-only, and repair now enforces an account-lockout policy
  (10 attempts → 15-minute lock) on every deployment as standing brute-force
  hardening.
- **Fenced additional users** (`scripts/add-vm-user.sh <Name> entry|review`):
  one command creates a non-administrator RDP user for an accountant (Tally +
  documents read/write) or an auditor (documents read-only; Tally opens with
  display-only enforced via Tally's own security users, which also give the
  Edit Log per-person attribution). repair.ps1 now fences `C:\TallyAI` (API
  key/config) and `C:\TallyData\Backups` to Administrators/SYSTEM on every
  converge. The multi-party network-access question is analysed and
  deliberately deferred in ADR-0019.

## [1.10.0] - 2026-07-27

### Added

- **Stable hostname (optional; ADR-0018):** set `dns_hostname` + `dns_zone` and
  the VM keeps that Route 53 A record pointed at its current public IP — the
  desktop, AI-app and RDP addresses never change again. Opt-in, zero cost,
  scoped IAM (one zone only), config via the assets pipeline, converged by
  repair, verified by the health check.

## [1.9.2] - 2026-07-26

### Fixed

- **Voucher ledger-entry amounts could carry the wrong value/sign** when an
  entry contained nested allocation blocks (BANKALLOCATIONS, BILLALLOCATIONS
  carry their own AMOUNT tags): entries are now parsed per
  ALLLEDGERENTRIES.LIST block with nested `*.LIST` sub-blocks stripped first.
  Found when the reconciliation engine refused to match 45 obviously-identical
  transactions during the first full-year live run (money-direction mismatch).

### Added

- Reconciliation matcher: a final **symmetric-group pass** pairs off leftovers
  when both sides hold equal-sized sets of identical (date, amount, direction)
  lines — e.g. two ₹400 government fees paid the same day — instead of
  reporting both sides unmatched. Ref-sharing pairs are consumed first within
  a group. With this and the amount-sign fix, the FY25-26 live run reconciles
  **299/299 statement lines** against the Tally bank ledger.

## [1.9.1] - 2026-07-26

### Fixed

- Two Tally-client bugs surfaced by first contact with real books: nested
  NAME.LIST tags corrupted master names, and ranged report exports ignore
  SVFROMDATE/SVTODATE over the gateway — voucher reads now use a
  current-period Voucher collection with in-code date filtering (and a
  period hint when the requested range lies outside Tally's Alt+F2 period).

## [1.9.0] - 2026-07-26

### Added

- **Bank reconciliation** (menu → 🏦; ADR-0016/0017): upload a statement
  (CSV parsed in code; PDF/photo read by AI with deterministic validation
  incl. running-balance continuity), pure-code matching against the Tally
  bank ledger (reference-number and amount/date passes), four-bucket report,
  one-tap application of bank-date ticks in Tally with per-voucher
  financial-fingerprint verification (batch stops on any discrepancy), and
  "Draft entry" handoff to Munshi for statement lines missing from the
  books. Parser/matcher covered by a local test; live Tally path awaits an
  open company.

## [1.8.0] - 2026-07-26

### Added

- **Read-only document browser** in the AI Accountant app (📁 button):
  browse Filed documents and the Drive inbox like a file explorer —
  breadcrumbs, view in browser, download — with no modification endpoints
  by construction.
- **Document search**: a local metadata index (no external search service)
  records voucher type, amount, ledgers, narration, date, and entry code at
  filing time (older files backfilled from the filename convention); the
  browser gets a live search box, and Munshi gets a `search_documents` tool
  ("find the July rent bill").

## [1.7.0] - 2026-07-26

### Added

- **Google Drive sync via rclone** (ADR-0015): Google's official Drive
  client turned out not to support Windows Server (verified — silent
  installer failure), so file sharing ships as rclone two-way sync instead:
  one-time "Set up Google Drive" desktop button (Google sign-in), then
  `C:\TallyData\Drive` ↔ the Drive `TallyCloud` folder every 5 minutes.
  rclone is a self-healed component; sync state is health-checked.

## [1.6.0] - 2026-07-26

### Added

- **Configurable Tally edition, Edit Log by default** (`tally_edition`
  variable; ADR-0014): repair stages TallyPrime Edit Log (TPEL — always-on
  audit trail, MCA-compliant for companies) unless `standard` is chosen.
  Edition changes re-stage the right installer on the desktop with a
  switch note; both mirror URLs join dynamic discovery and the weekly
  link check.

## [1.5.0] - 2026-07-26

### Changed

- **AI Accountant UI rebuilt on Tailwind CSS** (build-time compiled
  stylesheet committed to the repo — no CDN, no runtime compiler; ADR-0013).
  Mobile-first polish throughout: toast notifications for every operation
  outcome, proper modals/bottom sheets replacing browser `prompt()`/`confirm()`
  (menu, large-amount double-check, clear-conversation), loading spinners and
  disabled states, removable photo previews, live Tally status chip, safe-area
  handling, and a "Lock app" action (new `/api/logout`).

## [1.4.0] - 2026-07-26

### Changed

- **AI Accountant hardening — writes are now structurally safe.** The model
  lost its direct write tools; `propose_entry` creates a draft, the UI renders
  a card, and posting happens only on the user's Confirm tap. Posting is
  idempotent (status flip + pre-post marker check against the day book),
  validates ledgers/balance/date server-side, requires typed-amount
  confirmation above ₹1 lakh, verifies every voucher by day-book read-back of
  its `[M-<id>]` marker, and appends to an audit log.

### Added

- **Automatic document filing**: bill photos are saved on confirmation under
  `C:\TallyData\Documents\FY<yy-yy>\<MM-Month>\<date>_<label>_M-<id>.jpg`
  (snapshot-backed), with the voucher narration carrying the code and path —
  two-way traceability between entries and source documents.

## [1.3.0] - 2026-07-26

### Added

- **AI Accountant ("Munshi")** — a Claude-powered, mobile-first chat app
  served from the VM at `https://<ip>:8444`. Reads ledgers/day book through
  TallyPrime's XML gateway, understands bill photos (vision), proposes
  entries in plain language, and posts vouchers/ledgers to Tally only after
  explicit user confirmation (debit=credit validated server-side). Pluggable
  LLM provider layer (Anthropic first: `claude-opus-5`, official SDK,
  server-side refusal fallbacks, prompt caching). Deployed via the assets
  bucket, converged by `repair.ps1` (npm deps, self-signed cert, firewall,
  scheduled task), health-checked on port 8444; config + history stay in
  `C:\TallyAI\data` across updates.

## [1.2.0] - 2026-07-26

### Added

- **DSC token sharing without subscriptions** (`6 - Share DSC Token` /
  `scripts/share-dsc.sh`): VirtualHere server auto-provisioned on the owner's
  Mac, connected to the VM's VirtualHere client through an SSH reverse tunnel.
  The VM's built-in OpenSSH server is now a self-healing repair component;
  its authorized key (the deployment key pair's public half) is delivered via
  the assets bucket; port 22 is open only to `allowed_cidr`.
- **ARCHITECTURE.md**: contributor documentation — actors, lifecycle flows
  (first boot, every-boot converge, live-update path, DSC tunnel), repo map,
  and the project invariants.

### Changed

- Info wallpaper redesigned twice from user feedback: compact top-right panel
  (clear of desktop icons), content-computed height (can't be cropped), and
  rendering at the display's actual resolution (DCV resizes with the browser).

### Fixed

- VirtualHere server download URL (vendor moved it — caught while automating).

## [1.1.0] - 2026-07-26

### Added

- **Self-healing VM**: all VM logic moved to `vm/` and delivered via a
  private, Terraform-managed S3 assets bucket; the VM re-syncs and runs an
  idempotent `repair.ps1` at every boot, via the new "Repair This Computer"
  desktop button, and remotely via `scripts/repair.sh`.
- **Dynamic TallyPrime URL discovery** from Tally's own site (newest release
  wins) with known-good mirror fallbacks.
- **Info wallpaper** (BGInfo-style, self-rendered): key locations, live
  software versions, and what-to-do steps; refreshes at every login.
- **Local help website** on the VM ("Help and User Guide" desktop shortcut):
  full manual, troubleshooting table, and FAQ — works offline.
- **Weekly external-URL check** (`linkcheck.yml` + `scripts/check-urls.sh`)
  alerting maintainers when a vendor download location moves.
- Health check extended: Claude Code verified by execution; wallpaper, help
  page, and self-repair task now checked.

### Fixed

- Claude Code first-boot install could half-fail (shims without package);
  now verified and retried.
- Adobe Reader detection for the 64-bit unified install path.

## [1.0.0] - 2026-07-26

### Added

- Terraform IaC for an on-demand Windows Server 2022 workstation on AWS
  (Mumbai): self-contained VPC, encrypted gp3 disk, termination protection,
  IMDSv2, replacement guards (`ignore_changes` on AMI/user_data).
- Browser desktop via Amazon DCV, with RDP and SSM Fleet Manager fallbacks.
- First-boot bootstrap: Chrome, Adobe Reader, 7-Zip, Notepad++, Java 8
  (32-bit + 64-bit for GST emSigner / TRACES WebSigner), Git, Node.js,
  Claude Code, TallyPrime installer with first-login auto-launch, government
  portal and DSC-utility desktop shortcuts, VirtualHere client.
- Cost controls: idle auto-stop alarm, monthly AWS Budget, SNS email alerts.
- Data safety: daily DLM snapshots (14 retained).
- Health checks: `scripts/check.sh` (AWS + on-VM via SSM) and an on-VM
  "Check System Health" desktop button.
- Zero-knowledge operation: numbered macOS double-click buttons (0–5),
  plain-language `USER-GUIDE.md`, friendly on-VM `READ-ME-FIRST.txt`.
- Tool-free deployment path via AWS CloudShell
  (`scripts/cloudshell-deploy.sh`) and secret-free share packaging
  (`scripts/make-share-zip.sh`).
- Duplicate-deployment guard when an account already has the workstation.
