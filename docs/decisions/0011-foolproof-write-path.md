# ADR-0011: Writes to Tally are draft → user tap → idempotent verified post

- **Status:** accepted
- **Date:** 2026-07-26

## Context

The worst failure for an AI accountant is a wrong entry written confidently.
v1 enforced "confirm before write" in the system prompt — a strong policy,
but still a promise from the model, not a guarantee from the system.

## Options considered

- **Prompt-policy confirmation** (v1) — works until the one conversation
  where the model misreads intent; unacceptable for books of account.
- **Text-based confirmation parsing** ("did the user say yes?") — moves the
  judgment, doesn't remove it.
- **Structural separation** — the model can only create drafts; the *user's
  UI tap* is the only trigger for the single code path that writes.

## Decision

`propose_entry` is the model's only write-adjacent tool. `lib/drafts.js` owns
posting: pending → posting flips synchronously before any I/O (double-tap →
409); a pre-post day-book check for the draft's `[M-<id>]` marker prevents
double-posting even after a lost response; ledgers are created/verified
first; debits=credits and date sanity are server-validated; entries ≥ ₹1 lakh
require typing the amount; after posting, the voucher is verified by reading
it back from the day book; every action appends to `audit.log`. There are
deliberately **no alter/delete tools** — mistakes are fixed by a proposed
reversal entry, preserving the audit trail as accounting practice expects.

## Consequences

- Wrong-writes become structurally impossible rather than unlikely; the
  model can be wrong safely.
- Every future Tally operation (inventory invoices, bill-wise refs, payroll)
  must ship as a new draft type through this same pipeline — never as a
  direct-write tool.
- Failed posts revert to `pending` so the user can retry after fixing the
  cause (e.g. Tally closed); the marker check makes the retry safe.
