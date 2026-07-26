# ADR-0008: DSC token sharing via VirtualHere over an SSH reverse tunnel

- **Status:** accepted
- **Date:** 2026-07-26

## Context

Indian statutory filings need a physical USB DSC token, which stays plugged
into the owner's local machine (a Mac) while signing happens in the cloud
VM's browser. USB must therefore travel over the network. Research findings:
RDP smart-card redirection works well from Windows clients but is unreliable
from macOS; VirtualHere's own NAT-traversal relay ("EasyFind") turned out to
be a **paid subscription** (initially assumed free — corrected to the user).

## Options considered

- **EasyFind relay** — simplest UX, but a subscription and third-party relay
  in the signing path.
- **Router port-forwarding to the Mac** — free, but non-technical users and
  CGNAT make it a support nightmare.
- **Tailscale/VPN** — works, but introduces a whole product + account for one
  monthly signing session.
- **SSH reverse tunnel** — the VM already trusts our keypair; Windows ships
  OpenSSH server; `ssh -R 7575:localhost:7575` carries VirtualHere's port
  with zero new services, zero cost, encrypted.

## Decision

VirtualHere server on the Mac (free single-device license), client on the VM,
connected through `ssh -R` into the VM's built-in OpenSSH server. Port 22 is
open only to `allowed_cidr`; the authorized key is the deployment keypair's
public half, delivered via the assets bucket and installed by repair.
Automated as button `6 - Share DSC Token`.

## Consequences

- Free and self-contained, but the tunnel needs button 6 running during
  signing — a deliberate "the token is only shared while you say so" property.
- Windows-laptop users skip all of it (native RDP smart-card redirection).
- OpenSSH on the VM is now a repair-converged component; anything else that
  needs a secure host↔VM channel can reuse it.
