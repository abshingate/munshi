# ADR-0002: Terraform IaC with a self-contained VPC in ap-south-1

- **Status:** accepted
- **Date:** 2026-07-26

## Context

The setup had to be shareable — "anyone can deploy this in their own AWS
account". The first apply also failed with "no matching EC2 VPC found": the
owner's account had no default VPC in Mumbai.

## Options considered

- **CloudFormation** — one-click launch links, no local tooling; but weaker
  ecosystem for contributors and harder local iteration.
- **Terraform + default VPC** — least code, but breaks in accounts without a
  default VPC (observed in production on day one).
- **Terraform + own minimal VPC** — ~40 extra lines (VPC, IGW, one public
  subnet, route table), zero NAT cost, works in any account.

## Decision

Terraform with a self-contained VPC (10.20.0.0/16, one public subnet).
Region defaults to ap-south-1 (latency + data residency for an Indian
accounting workload). Windows AMI resolved via AWS's public SSM parameter.

## Consequences

- Deploys are account-agnostic — key to the share-zip / CloudShell story.
- No NAT gateway: the instance needs a public IP for egress (see ADR-0004's
  security-group compensations).
- Terraform state is local to the owner's machine by design (single-operator
  model); multi-operator access is by copying the folder (documented), not a
  remote backend — revisit if this ever becomes multi-admin.
