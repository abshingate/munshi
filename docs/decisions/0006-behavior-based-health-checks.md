# ADR-0006: Health checks test behavior, not file presence

- **Status:** accepted
- **Date:** 2026-07-26

## Context

Incident: the Claude Code install half-failed on first boot — npm wrote the
launcher shims but the package itself never landed. The health check tested
`Test-Path claude.cmd`, which passed, so the system reported all-green while
the feature was broken. The user found it before we did.

## Options considered

- **Keep presence checks, add more of them** — more of the same false
  confidence; a shim, an empty file, or a stopped service all "exist".
- **Behavior checks** — actually run the thing: `claude --version` must
  answer, DCV must be *listening* on 8443, portals must be *reachable*, the
  app must *serve* on its port.

## Decision

Every health check asserts observable behavior. Where a check can't run the
real operation (e.g. posting a voucher), it checks the closest behavioral
proxy. The same principle extends into the app: vouchers are verified by
reading them back (ADR-0011).

## Consequences

- Checks are slower (seconds, not milliseconds) — acceptable for an
  on-demand diagnostic.
- Invariant #4 in ARCHITECTURE.md; PR reviews should reject `Test-Path`-style
  assertions for anything that can be executed instead.
- The repair loop pairs with it: a FAIL line always names its fix, usually
  "run Repair" (invariant #5 — every failure path has a visible next step).
