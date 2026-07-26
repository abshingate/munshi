# Contributing to Tally Cloud Workstation

Thank you for considering a contribution! This project's goal is simple:
**a non-technical accountant must be able to use the result.** Every change is
judged against that bar.

## Ground rules

- Be kind and constructive — see our [Code of Conduct](CODE_OF_CONDUCT.md).
- Never commit secrets: no AWS keys, `.pem` files, `terraform.tfstate`,
  `terraform.tfvars`, account IDs, or personal IP addresses. The `.gitignore`
  protects the common cases — don't fight it.
- User-facing text (USER-GUIDE.md, VM read-me, script output) must stay in
  plain language. If your change adds jargon there, rewrite it.

## Development setup

```bash
git clone https://github.com/abshingate/tally-cloud-workstation.git
cd tally-cloud-workstation
terraform init -backend=false
```

You don't need an AWS account to contribute to most of the project — fmt,
validate, and linters run offline. Deploy-testing changes end-to-end costs a
few rupees of EC2 time; `terraform destroy` when done (test copies only!).

## Before opening a PR

Run what CI runs:

```bash
terraform fmt -recursive
terraform init -backend=false && terraform validate
shellcheck scripts/*.sh          # brew install shellcheck
```

If you touched `userdata.ps1`, keep the `<powershell>`/`<persist>` wrapper
tags intact and remember it must be valid PowerShell 5.1 (Windows Server's
built-in version).

## Pull requests

- Keep PRs focused — one topic per PR.
- Describe *why*, not just *what*, in the description.
- Update `CHANGELOG.md` under an `Unreleased` heading.
- CI must be green; a maintainer will review after that.

## Design principles (the short version)

1. **Data survives everything except deliberate destruction** — never weaken
   termination protection, snapshots, or the `ignore_changes` guard on the
   instance without a very good reason.
2. **Stopped-by-default economics** — features must not require the VM (or any
   new billable resource) to run continuously; keep idle cost near storage-only.
3. **Idempotent everywhere** — every script must be safe to run twice.
4. **Degrade gracefully** — every remote-access path needs a fallback
   (DCV → RDP → Fleet Manager); every install step needs a manual escape hatch.
