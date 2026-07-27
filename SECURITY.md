# Security Policy

## Supported versions

The `main` branch and the latest release are supported with security fixes.

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

- Preferred: [open a private security advisory](https://github.com/abshingate/munshi/security/advisories/new)
- Or email: abshingate@exadatum.com

You can expect an acknowledgement within a few days. Please include
reproduction steps and affected files. Coordinated disclosure is appreciated —
we'll credit you in the release notes unless you prefer otherwise.

## Scope notes

This project deploys infrastructure into *your own* AWS account. Things that
are deliberate, documented trade-offs (not vulnerabilities):

- The instance has a public IP; ingress is restricted to the owner's /32.
- Egress is unrestricted (user workstation reaching the internet).
- RDP/DCV exposure depends on the user keeping `allowed_cidr` current.

Reports that *tighten* these defaults without hurting usability are very welcome
as regular issues/PRs.
