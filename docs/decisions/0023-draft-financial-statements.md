# ADR-0023: Generating draft financial statements from Tally

- **Status:** accepted
- **Date:** 2026-07-29
- **Related:** ADR-0022 (Tally knowledge base)

## Context

Preparing annual financial statements for audit is one of the most tedious and
error-prone tasks a small company faces. The data already exists in Tally; what
is missing is the Schedule III presentation the Companies Act 2013 requires.

The question that prompted this: *"Do we have capability to generate Financial
Statements as Company that we can send to CA for audit?"*

## Decision

Generate **draft, clearly-labelled-unaudited** statements from Tally's ledger
balances: Trial Balance, Balance Sheet, Statement of Profit and Loss, plus the
ledger detail behind every line.

### What makes this safe rather than reckless

A tool that produces something *looking* like audited financials is dangerous.
Three properties keep it honest:

1. **The output declares what it is.** Every document opens with a DRAFT —
   UNAUDITED banner listing what has *not* been done: no provisions, accruals,
   cut-off adjustments, depreciation recomputation, tax provision, or notes.
   It closes with an eight-point list of what the auditor must still do.

2. **It refuses to look finished when it isn't.** If Equity & Liabilities does
   not equal Assets, the document says **"DOES NOT BALANCE — do not send until
   resolved"** in place of a total. If any ledger's Tally group has no
   Schedule III mapping, an "UNMAPPED — REVIEW REQUIRED" section lists it. A
   silently-dropped ledger would still balance and still be wrong.

3. **The Trial Balance is included.** It is the bridge between Tally and the
   statements, and the auditor's usual starting point. Nothing is presented
   that cannot be traced back to a ledger and, through ADR-0022, to a voucher.

### Deliberately NOT automated

Judgement, not arithmetic: provisions and accruals, depreciation policy under
Schedule II, current and deferred tax, investment valuation, going concern,
impairment, related-party disclosures, the notes, and the Directors' and
Auditor's reports. A statutory audit requires an independent CA regardless of
draft quality — this reduces preparation effort, not the audit.

## Implementation notes

Three bugs found during construction, each of which produced a plausible-looking
but wrong statement:

- **Tally's synthetic root arrives as the literal text `&#4; Primary`** — an
  unresolved XML numeric character reference, not a control byte. Stripping
  `\x00-\x1f` does nothing, so every ledger walked up to it: 61 of 66 ledgers
  unmapped and the entire balance sheet collapsed into one bucket. Strip
  numeric entities *as text*, and stop the walk one level below the root, where
  the real groups (Capital Account, Fixed Assets, Indirect Expenses) live.

- **Double-counting the year's result.** Tally's `Reserve & Surplus` closing
  balance already includes the current year's profit or loss — which is why
  balance-sheet ledgers sum to zero on their own. Adding profit again to Equity
  produced a difference *exactly equal to the profit figure*.

- **Sign convention.** Tally is credit-positive/debit-negative. Income carries
  credit balances, expenses debit ones. Flipping both made income print as
  negative and inverted the profit sign, turning a ₹46.28 lakh loss into an
  apparent profit.

The balance check caught the second bug before any output could be sent. That
is the point of having it: **an arithmetic invariant the tool cannot talk
itself out of.**

## Consequences

**Good.** A complete draft for any year from FY2016-17 onward, in minutes,
traceable to source. The CA receives a Trial Balance and mapped statements
rather than a Tally backup, which should reduce both fees and turnaround.

**Risk.** Draft statements could be mistaken for final ones. Mitigated by the
banner, the unresolved-item lists, and the refusal to total when unbalanced —
but presentation is a defence, not a guarantee. The covering note to the CA
should always say these are machine-generated drafts.

**Constraint.** Requires Tally running with the company loaded.
