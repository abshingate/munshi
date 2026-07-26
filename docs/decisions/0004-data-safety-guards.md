# ADR-0004: Layered data-safety guards; the instance is never replaced by a routine apply

- **Status:** accepted
- **Date:** 2026-07-26

## Context

"I can't lose data" was the strongest requirement. Two silent Terraform
behaviors could destroy the machine: AWS publishes a new Windows AMI monthly
(the SSM-parameter data source changes → forces replacement), and any
user_data edit forces replacement. Either would wipe the disk on a routine
`terraform apply`.

## Options considered

- **Pin the AMI ID** — stops the monthly churn but rots over time and still
  leaves user_data replacement.
- **`lifecycle.ignore_changes = [ami, user_data]`** — the instance is created
  once and never replaced by an apply; updates flow through other channels.

## Decision

`ignore_changes` on ami and user_data, plus `disable_api_termination`,
encrypted gp3 root volume, and DLM nightly snapshots (14 retained, 2 AM IST).
Security group ingress is restricted to the owner's /32 for every port; egress
is open (user workstation) — accepted trade-off, annotated for tfsec.

## Consequences

- **`terraform destroy` is the only destructive command in the project** —
  treated accordingly everywhere (docs, guides, duplicate-deploy guard).
- Live VMs can never be updated via user_data — which forced ADR-0005's
  assets-bucket architecture (a better channel anyway).
- Snapshots make every other mistake recoverable to within 24h; wrong-writes
  in the books have a finer-grained answer in ADR-0011's audit trail.
