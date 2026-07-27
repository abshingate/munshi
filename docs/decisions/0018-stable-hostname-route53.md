# ADR-0018: Stable hostname via boot-updated Route 53 record

Date: 2026-07-27

## Status

Accepted

## Context

The workstation's public IP changes on every start, so the browser-desktop,
AI-app and RDP addresses change too. Users must re-read the address from the
Turn ON button's output each time, bookmarks go stale, and any additional user
(e.g. an accountant connecting over RDP) must be told the current address.

Operators often already own a domain. Two ways to give the machine a permanent
address:

1. **Elastic IP** — a reserved static IP attached to the instance. Simple, but
   AWS now charges for EIPs at all times (~$3.6/month, roughly half this
   project's entire idle cost) and it still leaves users typing a raw IP
   unless DNS is layered on top anyway.
2. **DNS record updated by the VM at boot** — an A record (e.g.
   `tally.example.com`) in the operator's existing Route 53 zone, upserted with
   the current public IP by a boot-time script. Free, and the address users see
   is a name, not a number.

## Decision

Option 2, opt-in and fully generic: `dns_hostname` + `dns_zone` Terraform
variables (empty by default = feature absent). Terraform looks up the zone,
grants the instance role `ChangeResourceRecordSets` on **that one zone only**,
and delivers `vm/dns-config.json` through the existing assets pipeline (like
`tally-edition.txt`), so nothing operator-specific enters the repository.
On the VM, `update-dns.ps1` (AWSPowerShell, IMDSv2) upserts the A record with
TTL 60; repair.ps1 registers it as an ONSTART task and runs it during every
converge; the health check verifies the name resolves to the machine's current
IP (WarnOnly).

A subdomain record is independent of the zone's other records, so an existing
website or email on the domain is untouched.

## Consequences

- One permanent address for the desktop (`:8443`), the AI app (`:8444`) and
  RDP — bookmarkable, printable, shareable with additional users.
- Zero added cost; no Elastic IP to manage or pay for.
- The client-side allowlist (`allowed_cidr`) is unaffected — this solves the
  *server* address changing, not callers' addresses.
- DNS propagation is bounded by the 60s TTL; after a boot the name is correct
  within about a minute — comparable to the machine's own boot time.
- The browser's self-signed-certificate warning remains (the DCV certificate
  is not issued for the hostname); acceptable for a private machine, and a
  future enhancement could provision a proper certificate for the name.
