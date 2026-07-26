# ADR-0005: VM logic delivered via an S3 assets bucket with boot-time convergence

- **Status:** accepted
- **Date:** 2026-07-26

## Context

Three pressures converged: EC2 user-data is capped at 16KB and runs exactly
once (a failed install stays broken forever); ADR-0004 forbids user_data
updates from reaching live VMs; and we kept needing to push script fixes to
the running machine.

## Options considered

- **Everything in user_data** — hit the 16KB ceiling as features grew; no
  update or self-heal path.
- **Fetch scripts from the GitHub repo at boot** — unlimited size, but makes
  every boot depend on an external service and a repo URL that could move —
  the exact fragility ADR-0007 exists to fight.
- **Terraform-managed S3 bucket in the user's own account** — `vm/*` uploaded
  on every apply (etag-diffed), VM syncs at every boot then runs an
  idempotent `repair.ps1`.

## Decision

Private S3 assets bucket (SSE-S3; name suffixed with the account ID for
global uniqueness). user_data shrinks to a <2KB loader. `repair.ps1` is the
single source of truth for installed software and re-converges at every boot,
from the desktop "Repair This Computer" button, and via `scripts/repair.sh`.

## Consequences

- The update loop is: edit `vm/` file → `terraform apply` → `repair.sh` (or
  next boot). No VM rebuilds, no SSM-pushed one-off patches drifting from git.
- No external dependency at boot beyond the user's own account.
- Everything on the VM must be idempotent (invariant #3) — repair runs
  repeatedly by design.
- Costs ~nothing; contents are public-repo scripts, so SSE-S3 (not KMS) and
  no versioning (git is the history) — annotated for tfsec.
