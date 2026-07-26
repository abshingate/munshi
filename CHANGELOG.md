# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

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
