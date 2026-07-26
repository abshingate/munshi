# Architecture Decision Records

Every significant design or technical decision gets a short record here:
the context we were in, the options we considered, what we chose, and why.
The code shows *what* we did; these records preserve *why* — so future
changes are made knowing the original reasoning instead of guessing at it.

**When to write one:** any decision someone might later want to reverse or
question — a technology choice, a security trade-off, a structural pattern,
a deliberate limitation. If a PR review could ask "why is it done this way?",
that answer belongs in an ADR. Copy `template.md`, number it sequentially,
and link it from the PR.

**Statuses:** `accepted` (in force) → `superseded by ADR-XXXX` (replaced —
never delete or rewrite history, add a new record).

| # | Decision | Status |
|---|---|---|
| [0001](0001-stopped-by-default-ec2.md) | Stopped-by-default EC2 instead of always-on VM, WorkSpaces, or a local PC | accepted |
| [0002](0002-terraform-own-vpc.md) | Terraform IaC with a self-contained VPC in ap-south-1 | accepted |
| [0003](0003-amazon-dcv-browser-access.md) | Amazon DCV for browser access, RDP + Fleet Manager as fallbacks | accepted |
| [0004](0004-data-safety-guards.md) | Layered data-safety guards; instance can never be replaced by a routine apply | accepted |
| [0005](0005-s3-assets-boot-converge.md) | VM logic delivered via an S3 assets bucket with boot-time convergence | accepted |
| [0006](0006-behavior-based-health-checks.md) | Health checks test behavior, not file presence | accepted |
| [0007](0007-external-download-resilience.md) | Multi-layer resilience for external download URLs | accepted |
| [0008](0008-dsc-ssh-reverse-tunnel.md) | DSC token sharing via VirtualHere over an SSH reverse tunnel | accepted |
| [0009](0009-zero-knowledge-ux.md) | Zero-knowledge operator UX: numbered buttons, CloudShell path, plain-language docs | accepted |
| [0010](0010-ai-accountant-architecture.md) | AI Accountant: Node + Anthropic SDK + Tally XML gateway, pluggable provider | accepted |
| [0011](0011-foolproof-write-path.md) | Writes to Tally are draft → user tap → idempotent verified post | accepted |
| [0012](0012-document-filing.md) | Bill documents on the filesystem (FY/month tree) cross-referenced in narrations | accepted |
