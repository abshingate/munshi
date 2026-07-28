# The compliance safety net — what the system catches, what you catch

*Written 29-07-2026, after a full day of real TDS work exposed four years of
accumulated errors. This is the honest division of labour between software and
the human who runs it. Companion to [ROADMAP.md](../ROADMAP.md).*

## The claim, stated carefully

Not *"compliance runs itself"*. That would be a promise no software can keep.

> **Routine compliance runs automatically. Anything unusual stops and asks.
> And the system can always show you what it did and why.**

Everything below follows from taking that sentence literally.

---

## What went wrong, and what could have caught it

A real day's findings, sorted by whether software could have prevented them.
This is the evidence base for everything that follows — not hypotheticals.

### Software would have caught these ✅

| What happened | What catches it |
|---|---|
| ₹3,000 TDS deducted on rent below the threshold — the ₹50,000 limit is **per month**, not per year | A rules table with `basis: per_month`, checked before any deduction |
| ARTH paid gross for four consecutive years; ~₹47,110 of 194J never deducted | Threshold monitoring per vendor per section, cumulative, checked at payment time |
| ~₹3,00,000 of payments to ARTH present in the bank, absent from Tally | Monthly bank↔books reconciliation |
| 11 of 12 rent-TDS challans unrecorded in an audited year | The same reconciliation |
| Q3 FY25-26 return filed 103 days late | Deadline tracking |
| Two invalid deductee PANs causing a stuck ₹200 default since FY 2017-18 | PAN validation before filing |
| FY 2026-27 not booked in Tally at all | Staleness monitoring on the books |

**Roughly two-thirds of what was found is in this category.** It is the
strongest argument for building the system.

### Software would NOT have caught these ❌

| What happened | Why it needs a human |
|---|---|
| Books show director salaries 17L/7L; the directors intended 12.6L each | The system cannot know what was *intended* |
| The CA advised "no TDS needed, the company has losses" | Requires judging whether to trust your advisor |
| ₹3,60,000 paid to a director, then reversed over a GST concern | Needs to know *why*, and whether the reasoning was sound |
| Purchases of ₹4.99L with no revenue and no inventory | Needs someone who knows what was bought |
| Whether to reopen a signed and audited year | A business decision with legal consequences |

No amount of automation reaches these. They need someone who knows the
business and is willing to ask "does that make sense?"

---

## Four limits worth stating plainly

1. **The law changes.** The Income-tax Act was rewritten for 2026 — section
   194J became payment code 1027, forms 24Q/26Q became 138/140. Any encoded
   rule is a snapshot with an expiry date, so rules carry `applies_from` /
   `applies_to` and February (post-Budget) is a standing review.
2. **Portals break without notice.** On 28-07-2026 the OLTAS challan-correction
   facility moved between two portals and then went down for maintenance
   mid-task. Anything depending on a portal must degrade gracefully and say
   so, never fail silently.
3. **The assistant is not always right.** During that same session it stated
   that a default related to rent TDS, reasoning from pattern instead of
   checking. The bank statement disproved it. **The operator's challenge —
   "are you sure? how did you find out?" — was the control that worked.**
4. **Evidence is sometimes simply absent.** Three financial years currently
   have no bank statement at all. A system that hides that gap is worse than
   one that reports it.

---

## The design principles that follow

### 1. Deterministic where it can be, explained where it can't

Statutory values are computed by table-driven code and unit-tested. The model
explains the result and cites the rule; it never derives the number.

The ₹3,000 error is the case for this: a rules table encoding
`threshold: 50000, basis: per_month` is right every time. A language model
reasoning about "fifty thousand" may not be.

### 2. Every rule carries its authority and its dates

A rule without a citation is not trusted, and the loader rejects it. A rule
without an effective period cannot answer questions about past years — which
is what compliance questions almost always are.

### 3. Absence is a finding, not a silence

The `coverage` table records what evidence exists per year. It is queried
*before* answering, so the honest response to "what happened in FY 2016-17?"
is *"Tally has entries but I hold no bank statement to verify them."*

An assistant that cannot say "I don't know" will invent an answer.

### 4. Exceptions are the product

Reconciliation's value is not the matches — it is the **non**-matches. A bank
line with no voucher is a missing entry; a voucher with no bank line is an
accrual or an error. Both surface immediately rather than at audit.

### 5. The human approves anything irreversible

Filing, paying, confirming: always a human action, on a screen showing what
is about to happen (ADR-0021). Speed is worth very little here; a wrong
filing costs far more time to unwind than it saved.

### 6. Show the working

Every answer cites its source — document, bank line, or voucher. Not a
courtesy: it is what makes the operator's challenge possible, and that
challenge is a real control.

---

## Build order

Each phase is useful alone and reduces a specific, evidenced risk.

**Phase 1 — Never miss a deadline or threshold.**
Deadline calendar with escalating reminders; cumulative threshold monitoring
per vendor per section; alerts *before* payment, not after.
*Prevents: the four-year ARTH accumulation, the 103-day-late return.*

**Phase 2 — Rules engine.**
Typed rate/threshold/due-date tables with citations and effective dates.
Deterministic computation of TDS, interest and penalties.
*Prevents: the per-month/per-year error; every arithmetic mistake.*

**Phase 3 — Continuous reconciliation.**
Monthly bank↔books, exceptions raised immediately, coverage tracked.
*Prevents: ₹3,00,000 sitting unrecorded; 11 missing challans.*

**Phase 4 — Assisted data entry** (ADR-0021).
Assistant fills, human approves every submit.
*Prevents: transcription errors; the invalid-PAN default.*

**Phase 5 — Evidence completeness.**
Every entry linked to its document; missing evidence reported per period.
*Prevents: the audit-by-excavation problem.*

**Phase 6 — Advisor cross-check.**
Where professional advice conflicts with an encoded rule, say so and cite
both. Not to override the advisor — to make the disagreement visible.
*Prevents: acting on "you have losses, no TDS needed" without a second view.*

---

## The working agreement

The system's job is to make mistakes **rare and visible**. The operator's job
is to read the exceptions and ask hard questions.

Two habits that already proved their worth on 28-07-2026:

- **"Are you sure? How did you find that out?"** — this caught a wrong answer
  that no automated check would have flagged.
- **"That doesn't match what I remember."** — this is how the salary
  discrepancy and the reversed director payment surfaced at all.

Neither is replaceable. Build the net; keep reading what falls into it.
