# ADR-0019: Multi-user remote access — challenge documented, solution deferred

Date: 2026-07-27

## Status

Accepted (deliberate deferral)

## Context

The workstation supports multiple fenced Windows users (e.g. an operator
Administrator, a data-entry Accountant, a display-only Auditor — Tally's own
security layer provides per-user roles and Edit Log attribution on top). They
connect over RDP, and the stable hostname (ADR-0018) gives them a permanent
address.

The unsolved part is **network admission**. The firewall admits only
`allowed_cidr` — designed for a single operator whose occasional ISP-assigned
IP change is fixed with one button. Third-party users (an accountant working
from their office, an auditor from anywhere) have unknown, changing IPs, so
the allowlist model imposes per-person, per-change manual updates. Opening
RDP/DCV to the internet instead is not acceptable: exposed RDP is among the
most brute-forced services on the internet.

Options analysed:

1. **Self-hosted access page (preferred when triggered):** the planned
   serverless start/stop control page, extended with per-user username/password
   logins; an authenticated login auto-allowlists the caller's current IP in a
   dedicated security group, scoped to the ports that user's role needs (RDP
   for staff, the AI-app port for phones). Self-contained in the operator's
   AWS account, no third-party dependency, ~zero cost, revocation = disabling
   a login. Also delivers phone start/stop and mobile AI-app access in the
   same feature.
2. **Overlay network (Tailscale or similar):** close inbound entirely; users
   join a mesh VPN. Strongest posture, free at this scale, but adds an
   external account dependency and per-device client software.
3. **AWS Fleet Manager (available today, nothing to build):** browser RDP via
   the AWS console with no open ports; requires scoped IAM logins per user.
   Clunkier UX; adequate as an interim.

## Decision

**Defer.** The machine is stopped whenever not in use — an off machine is
unreachable regardless of firewall rules — and no third-party user works on it
daily yet. At the current scale the allowlist model plus the one-click IP fix
is adequate, and Fleet Manager already covers the occasional
"connect from anywhere" need with zero exposure.

**Trigger for implementation:** onboarding a third-party daily user (accountant/
auditor) or moving the machine to always-on operation. When triggered, the
default direction is option 1 (self-hosted access page with per-user logins),
with option 2 as the alternative if an even stronger posture is wanted.

## Consequences

- Today: additional users connect from allowlisted addresses only; adding or
  refreshing an address is a one-line security-group change; Fleet Manager is
  the from-anywhere fallback.
- The challenge and its analysed solutions are recorded here so the future
  implementation starts from a decision, not a rediscovery.
