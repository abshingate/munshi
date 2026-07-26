# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [1.6.0] - 2026-07-26

### Added

- **Configurable Tally edition, Edit Log by default** (`tally_edition`
  variable; ADR-0014): repair stages TallyPrime Edit Log (TPEL — always-on
  audit trail, MCA-compliant for companies) unless `standard` is chosen.
  Edition changes re-stage the right installer on the desktop with a
  switch note; both mirror URLs join dynamic discovery and the weekly
  link check.

## [1.5.0] - 2026-07-26

### Changed

- **AI Accountant UI rebuilt on Tailwind CSS** (build-time compiled
  stylesheet committed to the repo — no CDN, no runtime compiler; ADR-0013).
  Mobile-first polish throughout: toast notifications for every operation
  outcome, proper modals/bottom sheets replacing browser `prompt()`/`confirm()`
  (menu, large-amount double-check, clear-conversation), loading spinners and
  disabled states, removable photo previews, live Tally status chip, safe-area
  handling, and a "Lock app" action (new `/api/logout`).

## [1.4.0] - 2026-07-26

### Changed

- **AI Accountant hardening — writes are now structurally safe.** The model
  lost its direct write tools; `propose_entry` creates a draft, the UI renders
  a card, and posting happens only on the user's Confirm tap. Posting is
  idempotent (status flip + pre-post marker check against the day book),
  validates ledgers/balance/date server-side, requires typed-amount
  confirmation above ₹1 lakh, verifies every voucher by day-book read-back of
  its `[M-<id>]` marker, and appends to an audit log.

### Added

- **Automatic document filing**: bill photos are saved on confirmation under
  `C:\TallyData\Documents\FY<yy-yy>\<MM-Month>\<date>_<label>_M-<id>.jpg`
  (snapshot-backed), with the voucher narration carrying the code and path —
  two-way traceability between entries and source documents.

## [1.3.0] - 2026-07-26

### Added

- **AI Accountant ("Munshi")** — a Claude-powered, mobile-first chat app
  served from the VM at `https://<ip>:8444`. Reads ledgers/day book through
  TallyPrime's XML gateway, understands bill photos (vision), proposes
  entries in plain language, and posts vouchers/ledgers to Tally only after
  explicit user confirmation (debit=credit validated server-side). Pluggable
  LLM provider layer (Anthropic first: `claude-opus-5`, official SDK,
  server-side refusal fallbacks, prompt caching). Deployed via the assets
  bucket, converged by `repair.ps1` (npm deps, self-signed cert, firewall,
  scheduled task), health-checked on port 8444; config + history stay in
  `C:\TallyAI\data` across updates.

## [1.2.0] - 2026-07-26

### Added

- **DSC token sharing without subscriptions** (`6 - Share DSC Token` /
  `scripts/share-dsc.sh`): VirtualHere server auto-provisioned on the owner's
  Mac, connected to the VM's VirtualHere client through an SSH reverse tunnel.
  The VM's built-in OpenSSH server is now a self-healing repair component;
  its authorized key (the deployment key pair's public half) is delivered via
  the assets bucket; port 22 is open only to `allowed_cidr`.
- **ARCHITECTURE.md**: contributor documentation — actors, lifecycle flows
  (first boot, every-boot converge, live-update path, DSC tunnel), repo map,
  and the project invariants.

### Changed

- Info wallpaper redesigned twice from user feedback: compact top-right panel
  (clear of desktop icons), content-computed height (can't be cropped), and
  rendering at the display's actual resolution (DCV resizes with the browser).

### Fixed

- VirtualHere server download URL (vendor moved it — caught while automating).

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
