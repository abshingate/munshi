# ADR-0001: Stopped-by-default EC2 instead of always-on VM, WorkSpaces, or a local PC

- **Status:** accepted
- **Date:** 2026-07-26

## Context

The owner does accounting roughly once a month (Tally + GST/PF/PT portals),
cannot lose data, wants minimal cost, and needs trivial start/stop. Usage is
~8–10 hours/month.

## Options considered

- **Always-on cloud VM** — simplest, but ~$100+/month for hours of monthly use.
- **Amazon WorkSpaces** — managed VDI, but monthly base fees exceed our
  stopped-instance cost, less control, and Tally licensing/persistence is the
  same either way.
- **Local PC** — no cloud cost, but single point of failure for data, no
  remote/phone access, and defeats the goal of working from anywhere.
- **Stopped-by-default EC2** — pay compute only when running (~$1.5/month at
  actual usage); EBS persists everything for ~$9/month.

## Decision

EC2 t3.large Windows Server 2022 in Mumbai, stopped by default. Idle auto-stop
alarm as a cost backstop, nightly snapshots for data safety.

## Consequences

- Total ~$10–12/month; features must never require the VM to run 24×7
  (invariant #2 in ARCHITECTURE.md).
- Public IP changes on every start — tooling (start scripts, fix-ip) must
  print/refresh it rather than assuming a stable address; an Elastic IP was
  deliberately skipped as unnecessary cost.
- Tally's license tolerates stop/start because it's the same persistent
  machine — replacement (not stopping) is the thing that must never happen.
