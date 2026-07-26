# ADR-0014: Tally edition is configurable, defaulting to Edit Log (audit trail)

- **Status:** accepted
- **Date:** 2026-07-26

## Context

Since 1 Apr 2023, MCA rules (proviso to Rule 3(1), Companies (Accounts)
Rules) require every company (Pvt Ltd/Ltd) keeping books on software to use
software whose audit trail (edit log) records every change and **cannot be
disabled**; auditors must report on it annually (Rule 11(g)), with 8-year
retention. Tally ships two builds: standard TallyPrime (edit log optional —
an auditor can flag its disable-ability) and TallyPrime Edit Log (TPEL,
always-on). Proprietorships/partnerships have no such mandate. This is an
open-source project — users are of every entity type — but the project owner
is a Pvt Ltd company.

## Options considered

- **Always install TPEL** — compliant for everyone, but forces the audit-log
  overhead and UI on entities that never need it, with no opt-out.
- **Always install standard** — non-compliant by default for companies; the
  users least likely to know about the rule are the ones it burns.
- **Configurable, defaulting to standard** — an unconfigured company deploys
  into non-compliance silently.
- **Configurable, defaulting to Edit Log** — safe-by-default: forgetting to
  configure yields the compliant build; opting down to standard is an
  explicit, documented choice.

## Decision

A `tally_edition` Terraform variable (`editlog` default | `standard`),
validated, delivered to the VM as `vm/tally-edition.txt` through the assets
bucket. `repair.ps1` stages the matching build (TPEL vs TP mirror paths, both
covered by dynamic URL discovery and the weekly link check). An
edition-marker file makes the staging idempotent and edition-switch-aware: if
the configured edition changes (or Tally was installed before this feature),
repair re-stages the right installer and places it on the desktop with a
"run to switch editions" note.

## Consequences

- Companies get MCA-compliant books by default; the same Tally license works
  for both builds, so the choice is free.
- The wider compliance posture already aligns: books data on a server in
  India (ap-south-1, ADR-0001/0002), daily backups (nightly snapshots,
  ADR-0004), and Munshi's no-alter/no-delete write path (ADR-0011) complement
  the statutory audit trail rather than fighting it.
- Switching editions on an existing machine is a user-run installer (data is
  compatible; the edit log covers entries from the switch onward) — the
  system stages and explains, the human clicks.
- Legal caveat recorded: the rule summary reflects mid-2026 understanding;
  users must confirm current requirements with their CA.
