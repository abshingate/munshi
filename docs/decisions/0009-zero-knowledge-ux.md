# ADR-0009: Zero-knowledge operator UX — numbered buttons, CloudShell path, plain-language docs

- **Status:** accepted
- **Date:** 2026-07-26

## Context

The stated bar: "user can be dumb", "no technical user at all". Early
iterations assumed a terminal, Terraform knowledge, and reading technical
docs — the owner explicitly challenged each assumption in turn.

## Options considered

- **Document the CLI well** — still assumes a terminal; fails the bar.
- **A native/GUI installer app** — heavy to build/maintain for what is
  fundamentally a handful of scripts.
- **Numbered double-click `.command` buttons** wrapping the scripts, plus a
  browser-only deployment path.

## Decision

Three tiers, lowest assumed knowledge wins: (1) macOS numbered buttons
`0-Setup … 6-Share DSC Token` — the number encodes the workflow order;
(2) AWS CloudShell (`scripts/cloudshell-deploy.sh`) for any-OS, zero-install
deployment — upload a zip, paste two lines; (3) raw Terraform for engineers.
Documentation splits by audience: USER-GUIDE.md (accountant, plain language,
rupee analogies), README.md (deployer), ARCHITECTURE.md (contributor). On
the VM: auto-opening READ-ME, offline help.html, and an info wallpaper.

## Consequences

- Every user-facing sentence must stay jargon-free (invariant #7); PR review
  enforces it.
- Everything must be safe to run twice — buttons get double-clicked
  (invariant #3); button 0 guards against duplicate deployments in the same
  account.
- macOS Gatekeeper's "unidentified developer" prompt is documented
  (right-click → Open) rather than solved with signing certificates — cost
  not justified for a folder shared person-to-person.
- Scripts must stay bash-portable (macOS + Linux/CloudShell): BSD vs GNU
  differences (sed -i, nc flags) already bit us and are handled.
