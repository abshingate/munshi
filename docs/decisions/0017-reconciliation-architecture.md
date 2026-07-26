# ADR-0017: Bank reconciliation — code matches, LLM extracts, alters verified

- **Status:** accepted
- **Date:** 2026-07-26

## Context

Reconciliation ties three things together: bank statement lines, Tally bank
vouchers, and (eventually, via bill-wise refs) invoices. It involves reading
messy vendor formats (every bank's CSV/PDF differs), deciding what matches,
and — per ADR-0016 — writing bank-date ticks onto existing vouchers, the one
alteration we permit.

## Options considered

- **LLM does everything** (read statement, decide matches, apply) — fast to
  build, but "the AI decided these matched" is not an audit answer, and
  extraction errors would propagate silently into the books.
- **Code does everything** — deterministic, but every bank format needs
  bespoke parsing, and PDFs/photos are out of reach.
- **Split by trust level** (chosen): the LLM may *read* and *suggest*; only
  deterministic code may *decide* and *write*, and every write is verified.

## Decision

Three trust tiers in `lib/recon.js` + `/api/recon/*`:

1. **Extraction**: CSV is parsed by code first (header detection, Indian
   number formats). PDFs/images/unrecognized CSVs go to the LLM — but every
   extraction (either path) passes deterministic validation, including a
   **running-balance continuity check** (each row's balance must equal the
   previous ± amount) that catches misread numbers cold.
2. **Matching is pure code**: staged passes — reference-number match, then
   unique amount+direction within tightening date windows. The LLM never
   marks a match. Output: matched / in-bank-only / in-books-only, each
   matched pair carrying its reason and confidence.
3. **Applying ticks** (the ADR-0016 exception): full voucher XML round-trip —
   export the voucher, inject only BANKERSDATE, re-import as Alter, then
   **re-export and compare the financial fingerprint** (every ledger line
   and amount must be byte-identical). Any discrepancy stops the batch
   immediately and is logged loudly. Sessions are idempotent (applied once).
   Missing entries never post directly — each "in bank, not in books" line
   is handed to Munshi as a chat prompt and flows through the ordinary
   ADR-0011 draft → confirm pipeline.

## Consequences

- A wrong extraction is caught by validation; a wrong match can't be
  invented by the AI; a corrupted alter is caught by the fingerprint check
  before a second voucher is touched. Failure of any tier degrades to
  "human looks at the report", never to silent wrong books.
- The alter path (partial XML surgery on Tally's voucher format) is the
  riskiest code in the project — it ships flagged for careful first use and
  gets its live end-to-end test once a real company is open; the
  fingerprint-verify makes even a wrong implementation loud rather than
  destructive.
- Statement files and the audit log together form auto-generated
  reconciliation working papers (see ADR-0016's compliance reasoning).
- Bill-wise invoice linkage remains the designed next step on top of this.
