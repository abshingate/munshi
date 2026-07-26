# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [1.1.0] - 2026-07-26

### Added

- **Self-healing VM**: all VM logic moved to `vm/` and delivered via a
  private, Terraform-managed S3 assets bucket; the VM re-syncs and runs an
  idempotent `repair.ps1` at every boot, via the new "Repair This Computer"
  desktop button, and remotely via `scripts/repair.sh`.
- **Dynamic TallyPrime URL discovery** from Tally's own site (newest release
  wins) with known-good mirror fallbacks.
- **Info wallpaper** (BGInfo-style, self-rendered): key locations, live
  software versions, and what-to-do steps; refreshes at every login.
- **Local help website** on the VM ("Help and User Guide" desktop shortcut):
  full manual, troubleshooting table, and FAQ — works offline.
- **Weekly external-URL check** (`linkcheck.yml` + `scripts/check-urls.sh`)
  alerting maintainers when a vendor download location moves.
- Health check extended: Claude Code verified by execution; wallpaper, help
  page, and self-repair task now checked.

### Fixed

- Claude Code first-boot install could half-fail (shims without package);
  now verified and retried.
- Adobe Reader detection for the 64-bit unified install path.

## [1.0.0] - 2026-07-26

### Added

- Terraform IaC for an on-demand Windows Server 2022 workstation on AWS
  (Mumbai): self-contained VPC, encrypted gp3 disk, termination protection,
  IMDSv2, replacement guards (`ignore_changes` on AMI/user_data).
- Browser desktop via Amazon DCV, with RDP and SSM Fleet Manager fallbacks.
- First-boot bootstrap: Chrome, Adobe Reader, 7-Zip, Notepad++, Java 8
  (32-bit + 64-bit for GST emSigner / TRACES WebSigner), Git, Node.js,
  Claude Code, TallyPrime installer with first-login auto-launch, government
  portal and DSC-utility desktop shortcuts, VirtualHere client.
- Cost controls: idle auto-stop alarm, monthly AWS Budget, SNS email alerts.
- Data safety: daily DLM snapshots (14 retained).
- Health checks: `scripts/check.sh` (AWS + on-VM via SSM) and an on-VM
  "Check System Health" desktop button.
- Zero-knowledge operation: numbered macOS double-click buttons (0–5),
  plain-language `USER-GUIDE.md`, friendly on-VM `READ-ME-FIRST.txt`.
- Tool-free deployment path via AWS CloudShell
  (`scripts/cloudshell-deploy.sh`) and secret-free share packaging
  (`scripts/make-share-zip.sh`).
- Duplicate-deployment guard when an account already has the workstation.
