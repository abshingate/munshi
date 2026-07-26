# ADR-0016: Narrow alteration exception — Munshi may set the bank date (reconciliation tick)

- **Status:** accepted (amends ADR-0011's "no alterations" rule with one scoped exception)
- **Date:** 2026-07-26

## Context

ADR-0011 forbids the AI from altering or deleting existing Tally vouchers —
mistakes become reversal entries. Bank reconciliation, however, is *marked*
in Tally by filling the **bank date** field on existing bank vouchers
("this entry appeared in the statement on date X"). Automating
reconciliation therefore requires touching existing vouchers, colliding
with the rule.

## Options considered

- **(a) Scoped exception** — a tool that can set *only* the bank-date field
  on a voucher, nothing else, and only after the user confirms the match.
- **(b) No exception** — Munshi produces the match report; the user applies
  ticks manually in Tally's native BRS screen each month.

## Decision

Option (a). The reconciliation tool's write capability is limited to the
bank-date field by construction; every tick is confirm-gated (the user
approves the match set before any is applied) and recorded in our audit log
with the evidence (statement line ↔ voucher pairing).

## Compliance reasoning (owner asked explicitly; discussed 2026-07-26)

- The MCA audit-trail mandate requires changes to be **recorded, not
  prevented**. The Edit Log edition captures the bank-date change like any
  other alteration, regardless of channel (UI or XML gateway).
- **TallyPrime's own auto bank reconciliation feature does exactly this** —
  imports a statement and sets bank dates programmatically. Widely used,
  routinely audited. Our version adds a maker-checker step (user confirms
  matches) that Tally's native feature lacks.
- Bank date changes no amount, ledger, party, or transaction date — no
  effect on trial balance, GST, or tax computations.
- Attribution nuance: Tally's edit log attributes gateway changes to the
  logged-in Tally user. Our append-only audit log supplies the finer-grained
  record (which statement line, which voucher, who confirmed, when) —
  auto-generated reconciliation working papers. Statement files are retained
  in the documents tree.
- Owner to mention the practice to the CA/auditor as a courtesy; no
  approval hurdle is expected given the above.

## Consequences

- The reconciliation feature can auto-complete the full loop: ingest
  statement → deterministic matching (code decides, LLM only suggests) →
  user confirms match set → ticks applied → unmatched lines become ordinary
  draft entries via the ADR-0011 pipeline.
- The exception must stay narrow: any future request to widen alteration
  powers (amounts, dates, ledgers, deletions) requires a new ADR and should
  be viewed with default suspicion — ADR-0011's reasoning still stands.
- Implementation must reject a bank-date write to any voucher not part of a
  user-confirmed match set (same idempotency/verification discipline as
  posting).
