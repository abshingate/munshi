# ADR-0012: Bill documents on the filesystem (FY/month tree) cross-referenced in narrations

- **Status:** accepted
- **Date:** 2026-07-26

## Context

Users send bill photos; audits require going from an entry to its source
document and back. TallyPrime's data file cannot store attachments (only
fragile third-party TDL add-ons bolt this on).

## Options considered

- **TDL attachment add-on** — vendor lock-in, breaks across Tally releases,
  data trapped in a proprietary blob.
- **Cloud storage (S3/Drive)** — survives the VM, but adds accounts, sync
  failure modes, and privacy questions for financial documents; the VM's
  disk is already snapshot-backed nightly.
- **Local filesystem tree + cross-reference** — plain files a human (or
  auditor) can browse with zero tooling.

## Decision

On confirmation (ADR-0011), bill images are filed to
`C:\TallyData\Documents\FY<yyyy-yy>\<MM-Month>\<date>_<label>_M-<id>.jpg`
— financial year April–March, month folder, ISO date, sanitized label, and
the draft's unique code. The voucher narration carries the same `[M-<id>]`
code plus the relative document path: voucher→bill and bill→voucher are both
one lookup.

## Consequences

- Documents live inside `C:\TallyData`, so the existing nightly snapshots
  back them up with the books — no new backup machinery.
- The filename alone tells you what/when/which-entry without opening anything.
- Files are copied on confirm (never on propose) and pending images are
  deleted on reject — no orphaned documents for entries that never happened.
- Tally narration length bounds what we embed: one code + one relative path;
  multiple attachments share the code and differ by suffix.
