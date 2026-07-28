# Munshi Roadmap — the AI accountant an SME never has to think about

*Munshi's promise: run your business; the munshi keeps the books, the evidence,
the deadlines and the auditor happy — and every action it takes is confirmed by
you, attributed by name, and provable afterwards. Tally stays the system of
record; the owner never has to open it.*

## Principles (non-negotiable, already embodied)

1. **Confirm-before-write.** The AI proposes; a human taps. Structurally
   enforced, not promised.
2. **Evidence-first.** Every entry is born holding its document; every document
   knows its entry. An audit is a lookup, not an excavation.
3. **AI proposes, code verifies.** Matching, totals, balances and read-backs
   are deterministic. The model never gets to declare success.
4. **Named accountability.** Edit-Log attribution per person (and for Munshi
   itself). Books that always know who did what, when.
5. **Your machine, your books.** Self-hosted first; nothing leaves the
   deployment that the owner didn't send.

**What this does and does not promise:**
[docs/compliance-safety-net.md](docs/compliance-safety-net.md) sets out
honestly which mistakes the system catches, which always need a human, and
in what order to build the net. Written from a real day's findings, not from
aspiration.

---

## Pillar 1 — Capture: every rupee's paperwork arrives by itself

- Photo of any bill → proposed entry (shipped)
- **Email-in address** (bills@…): forward an invoice, it's filed and proposed
- **WhatsApp capture**: snap → send → confirm from chat
- Gmail/IMAP watcher: finds invoices in the inbox (Amazon, AWS, SaaS receipts)
- **Vendor-portal fetchers**: auto-download monthly invoices (AWS, Google,
  cloud/SaaS vendors) — no more "₹3,300 of missing invoices"
- Drive/folder inbox watcher (shipped: Drive sync + filing)
- Bank-SMS/UPI-notification parsing for instant expense stubs
- Batch mode: shoebox of 50 photos → one review session
- Voice notes: "paid five thousand to the electrician yesterday, cash"
- Recurring-bill recognition: rent, subscriptions, EMIs propose themselves
- Statement importers: bank CSV/PDF (shipped), credit cards, PhonePe/GPay
  exports, payment-gateway settlements (Razorpay/Stripe), marketplace reports
  (Amazon/Flipkart seller)

## Pillar 2 — The bookkeeping brain

- Ledger auto-suggestion learned from this company's own history
- Party auto-create with **GSTIN lookup/validation** (name, address, status)
- **Duplicate-invoice detection** (content-hash + invoice-number)
- **Marketplace clubbing**: one UPI debit = many invoices; match to the paisa
- **Card-reimbursement cycles**: card statement ↔ personal-spend ↔ company
  reimbursement, itemised — never again a "director advance" made of paperwork
- **Personal-vs-business flagging**: director-ledger movements challenged at
  entry time, not at year-end
- TDS-aware entries: auto-compute 194C/J/I/H on qualifying payments
- RCM/import detection for foreign SaaS invoices
- **Asset-vs-expense advisor** (capitalization suggestions with Schedule II
  lives; "this drone looks like a fixed asset")
- Multi-line narration standards with searchable codes (shipped: [M-…])
- GST input-credit eligibility tagging per invoice
- Round-off/approximation reconciliation notes (auto)

## Pillar 3 — Reconciliation as a habit, not a project

- Bank ↔ books auto-recon with deterministic matching (shipped: 299/299 engine)
- Scheduled monthly recon with a one-tap "apply ticks" ritual
- Credit-card statements as first-class recon sources
- Inter-account transfer detection (bank↔FD↔investment, never "income")
- Refund/reversal pairing (order → refund → net)
- Subscription tracker: what recurs, what changed price, what's zombie
- Investment/FD registry: interest accrual, TDS-on-interest capture, 26AS tie
- **Books Health Score**: one number — % of transactions matched, papered,
  attributed. The 299/299 experience, productised.

## Pillar 4 — Compliance that arrives before the deadline

- India compliance calendar: GSTR-1/3B, TDS challans (7th) & returns (24Q/26Q),
  EPF (15th), PT, advance tax, ROC (AOC-4/MGT-7), ITR — per entity type
- **Deadline nudges with money attached**: "TDS ₹5.5L due in 3 days; late = X"
- Challan preparation packs: amounts, heads, portal steps, receipts filed back
- GSTR data preparation from books; mismatch preview vs 2A/2B
- Form 16 / salary-TDS annual cycle
- Audit-trail compliance posture (shipped: Edit Log default, MCA rules)
- Penalty-avoided ledger: what Munshi's nudges saved this year
- Year-end close checklist: provisions, depreciation runs, confirmations

## Pillar 5 — Money awareness (the owner's daily question: "are we fine?")

- Cash position + 90-day cash-flow forecast from recurring patterns
- Runway and burn for build-phase companies
- **Receivables chasing**: polite automatic reminders, escalation ladder
- Payables planning: what's due, what's early-payment-worthy
- Budget vs actual with drift alerts
- GST credit balance and blocked-credit watch
- "Ask anything" analytics in chat: top vendors, spend by category, YoY

## Pillar 6 — People & payroll

- Salary structures with statutory awareness (basic/HRA/PF ceilings)
- Monthly payroll journals + payslips generated and filed
- PF/PT/TDS per employee; challan-ready totals
- Reimbursement policy engine: submit → approve → pay → file — no orphan
  advances, ever
- Contractor payments with 194C/J tracking and certificates
- Director remuneration governance: board-resolution reminders, §188 threshold
  watch for relatives' pay

## Pillar 7 — The advisor in the room

- **Anomaly watchdog**: balances that creep (a director advance growing month
  on month gets flagged in month two, not year three)
- **Related-party sentinel**: §185/186/188 and 2(22)(e) exposure surfaced with
  plain-language explanations
- Tax-optimization hints: rebate thresholds, regime comparisons, timing
  ("₹11.92L vs ₹12.6L changes nothing; ₹12.4L would")
- What-if scenarios: salary vs distribution, buy vs lease, capitalize vs expense
- Draft notes-to-accounts and FS-adjustment summaries for the CA (shipped:
  Schedule III FS generator — `docs/fs-generator.md`)
- Plain-language monthly letter: "what happened in your books this month"

## Pillar 8 — CA & auditor collaboration (the handoff, productised)

- **One-click CA Pack**: books backup + rectification record + evidence zips +
  mapping CSV + findings summary — the For-CA folder as a feature
- Voucher-level query threads: CA asks, owner answers, evidence attaches,
  resolution recorded
- Read-only auditor access links (documents + reports, no edit surface)
- Sign-off workflow: draft FS in → owner review → e-sign-ready out
- Handoff briefs between accountants: state of books, open items, conventions
- Evidence packs per topic on demand ("everything behind rent, FY25-26")

## Pillar 9 — Conversation & channels

- Mobile-first chat PWA (shipped) with camera, drafts, confirmations
- **WhatsApp as a first-class channel** (the SME's real UI)
- Email interface for longer requests and reports
- Hinglish + regional-language understanding
- Daily digest ("yesterday: 3 entries, 1 pending confirmation, GST in 6 days")
- Weekly close ritual: 10 minutes, everything reviewed, health score updated
- Voice conversations for hands-busy owners

## Pillar 10 — Trust, control, auditability (the moat)

- Structural confirm-before-write (shipped)
- Typed-amount double-check above thresholds (shipped)
- Verify-after-write day-book read-back (shipped)
- Traceable entry markers (shipped)
- **Maker-checker flows**: accountant proposes, owner approves, Munshi posts
- Per-user Munshi identities; Tally security-user integration
- Undo window with clean reversal entries (never silent deletes)
- Explainability: every proposal cites its evidence and its precedent entries
- Hallucination guards: deterministic validators on amounts, dates, GSTINs,
  ledger existence — the model cannot invent a fact the code didn't verify
- Immutable action log alongside Tally's Edit Log

## Pillar 11 — Platform & operations

- Self-hosted on the owner's cloud (shipped: the workstation) and a managed
  SaaS tier for those who want zero ops
- Multi-company, multi-FY navigation
- Backup/restore rituals (shipped: nightly + on-demand), restore drills
- Tally release/licence awareness: TSS expiry warnings, version-compat checks
  before backups travel to the CA
- Health self-checks and self-healing (shipped)
- Stable addresses, fenced users, role logins (shipped)
- Account Aggregator (AA) integration for consented direct bank feeds — the
  end of statement uploads

## Pillar 12 — Onboarding: day one to trustworthy books

- **Books takeover wizard**: restore the CA's backup, verify, baseline
- **Historical cleanup assistant**: the FY25-26 forensic exercise as a guided
  product — tie out a year, find the paperwork, propose rectifications
- Opening-balance verification against bank/FS
- "Meet your books" tour: what you own, owe, spend, earn — in plain words
- Migration importers: Excel books, other software exports

---

## Sequencing

**Now (the daily-use core):** WhatsApp + email capture · Gmail invoice watcher
· recurring recognition · monthly recon ritual · compliance calendar with
nudges · CA Pack button · Books Health Score.

**Next (the lifesaver tier):** vendor-portal fetchers · receivables chasing ·
payroll cycle · anomaly watchdog · maker-checker · query threads · AA bank
feeds.

**Later (the category-definer):** advisor scenarios · multi-company SaaS ·
regional languages · marketplace/gateway ecosystem · guided historical
cleanups as a service.

*Every feature above traces to a real wound: a missing invoice, a mislabelled
advance, a deadline met at 11 pm, a handoff rebuilt by hand. Munshi exists so
no SME bleeds the same way twice.*
