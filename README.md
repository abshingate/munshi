# Tally Cloud Workstation

[![CI](https://github.com/abshingate/tally-cloud-workstation/actions/workflows/ci.yml/badge.svg)](https://github.com/abshingate/tally-cloud-workstation/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Terraform](https://img.shields.io/badge/Terraform-%E2%89%A51.5-844FBA?logo=terraform&logoColor=white)](https://developer.hashicorp.com/terraform)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A pay-only-when-you-use-it Windows machine on AWS for monthly accounting and
compliance work (TallyPrime, GST/PF/PT/Income-tax portals). The machine stays
**stopped** most of the month — you start it, work for a few hours, stop it —
and all data persists forever and is snapshotted daily.

```mermaid
flowchart LR
    subgraph you["You"]
        B["Browser / RDP client"]
        T["DSC USB token"]
    end
    subgraph aws["AWS ap-south-1 · your account"]
        subgraph vpc["VPC 10.20.0.0/16"]
            EC2["Windows Server 2022\nTallyPrime · Java 8 · Chrome\nAmazon DCV · Claude Code"]
        end
        SNAP["Nightly EBS snapshots\n(14 kept)"]
        ALARM["Idle auto-stop alarm"]
        SNS["Email alerts + budget"]
        SSM["SSM / Fleet Manager"]
    end
    B -- "HTTPS 8443 (DCV) / RDP 3389\nonly from your IP" --> EC2
    T -. "smart-card redirection\nor VirtualHere" .-> EC2
    EC2 --> SNAP
    ALARM -- "stop when idle" --> EC2
    ALARM --> SNS
    SSM -- "health checks & browser fallback" --> EC2
```

**Typical cost: ~$10–12/month (~₹900–1,000)** for ~8–10 hours of monthly use
(mostly disk storage), versus $100+ for a machine running 24/7.

## What you get

| | |
|---|---|
| Machine | Windows Server 2022, t3.large (2 vCPU / 8 GB), 100 GB encrypted disk, Mumbai (`ap-south-1`) |
| Access | **Browser** via Amazon DCV (`https://<ip>:8443`), or RDP, or AWS Console → Fleet Manager |
| Stable address (optional) | Own a domain on Route 53? Set `dns_hostname = "tally.example.com"` and the VM updates that DNS record itself at every boot — one permanent address for the desktop, the AI app and RDP, no Elastic IP needed (ADR-0018) |
| Pre-installed | Chrome, Adobe Reader, 7-Zip, Notepad++, **Java 8 (32-bit + 64-bit — required by GST emSigner / TRACES WebSigner)**, **Google Drive sync** (via rclone — the official client doesn't support Windows Server, ADR-0015; one-time sign-in button, then `C:\TallyData\Drive` ↔ your Drive's `TallyCloud` folder every 5 min), Amazon DCV, IST timezone, desktop shortcuts for GST / Income-tax / TRACES / EPFO / ESIC / MCA portals and DSC utilities |
| Data safety | Disk persists across stop/start · daily snapshots (14 kept) · termination protection on |
| Cost safety | Auto-stops after ~1 hour of idle CPU, so forgetting it never costs a full month |
| Alerting | Email on auto-stop events + AWS Budget emails at 80%/100% of monthly budget (set `alert_email`) |
| Claude | Git, Node.js LTS and the Claude Code CLI pre-installed — run `claude` on the VM |
| Health checks | `./scripts/check.sh` locally + "Check System Health" on the VM desktop |
| Self-healing | Every install re-verified at each boot; "Repair This Computer" button + `./scripts/repair.sh` reinstall anything broken; Tally's download URL is discovered live from their site |
| On-VM help | "Help and User Guide" desktop page (works offline) + an info wallpaper showing locations, versions, and what to do when something breaks |
| AI Accountant | "Munshi" — a Claude-powered accountant chat app on the VM (`https://<ip>:8444`, mobile-first): send bill photos, ask questions, and it reads/posts Tally entries with confirm-before-write discipline |

## Three audiences, three documents

- **This README** is for the (technical) person who deploys and maintains the setup.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** is for contributors — how the system
  works internally, lifecycle flows, and the invariants changes must respect.
- **[USER-GUIDE.md](USER-GUIDE.md)** is for the person who *uses* the machine —
  written in plain language, no jargon. Give them that file and the numbered
  `*.command` buttons in this folder (`1 - Turn ON Tally Computer`, `2 - Get
  Password`, `3 - Check Everything OK`, `4 - Fix Connection Problem`, `5 - Turn
  OFF Tally Computer`) — each is a double-click, no terminal needed. On the VM
  itself, `READ-ME-FIRST.txt` on the desktop covers first-time setup the same way.

## Prerequisites

- An AWS account (see below if you've never had one)
- A TallyPrime license (Silver single-user is enough; activated once, on the machine)
- On a Mac, button `0` installs the tooling ([AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.5) automatically; install them yourself on other platforms

**Never had an AWS account?** This is the one genuinely manual part (Amazon
requires it): sign up at [aws.amazon.com](https://aws.amazon.com) with an
email, a credit/debit card, and phone OTP verification (~10 minutes). Then
create the access keys button `0` will ask for: AWS Console → IAM → Users →
Create user → attach `AdministratorAccess` → Security credentials → Create
access key. Everything after that is automated.

## Deploy (one time)

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set allowed_cidr to "<your-ip>/32"
#   (find your IP with: curl -s https://checkip.amazonaws.com)

terraform init
terraform apply
```

Then wait ~10 minutes on first boot while software installs, and:

```bash
./scripts/get-password.sh   # Windows Administrator password (save it in a password manager)
./scripts/start.sh          # prints the browser + RDP address (already running after apply)
```

**First login (one time, ~5 min, no technical skill needed):** open
`https://<ip>:8443` in your browser (accept the self-signed-certificate
warning) and log in as `Administrator`. The TallyPrime install wizard **opens
by itself** — click Install, set the data folder to `C:\TallyData`, then enter
your Tally serial to activate the license. That's it; `READ-ME-FIRST.txt` on
the desktop walks through it.

Two things genuinely cannot be pre-installed by *any* automation, so they are
one double-click on first use instead (shortcuts are on the desktop):

- **Portal signer utilities** (GST emSigner, TRACES WebSigner): the portals
  only let *you* download them after logging in to *your* account. Their
  prerequisite — 32-bit Java 8 — is already installed, so it's download → Next
  → Finish.
- **Your DSC token's driver** (ePass2003 / ProxKey / mToken): depends on which
  brand of token you own — run the matching link in the desktop "DSC Setup"
  folder once.

## Everyday use

```bash
./scripts/start.sh     # ~2 min to boot, prints the current IP
# ... work in the browser (https://<ip>:8443) or via RDP ...
./scripts/stop.sh      # billing drops to storage-only
./scripts/status.sh    # is it running? what's the IP?
./scripts/check.sh     # full readiness check — AWS side + on-VM health via SSM,
                       # every problem highlighted with how to fix it
```

On the machine itself, the desktop has **"Check System Health"** (same checks,
for the non-technical user) and **"Claude Code"** — Claude runs on the VM too
(Git + Node.js + Claude Code CLI are pre-installed; sign in to your Anthropic
account on first run).

The public IP changes on every start — `start.sh` always prints the current one.
Prefer a desktop client? Use **Microsoft Remote Desktop** (free on the Mac App
Store) with the IP from `start.sh`.

## The AI Accountant ("Munshi")

A Node.js web app (`vm/app/`) served from the VM on **`https://<ip>:8444`** —
open it on any phone/laptop on your home network (same IP the firewall already
allows) or via the "AI Accountant" desktop shortcut on the VM.

- **What it does**: chat with an AI accountant that is connected to TallyPrime
  through Tally's XML gateway (localhost:9000). It reads your ledgers and day
  book, answers questions ("what did I spend this month?"), extracts bill
  photos (vision), proposes the correct double-entry voucher in plain
  language, and — **only after you confirm** — posts it to Tally, creating any
  needed ledgers under the right groups.
- **Engine**: Claude (`claude-opus-5`) via the official Anthropic SDK, with
  server-side refusal fallbacks enabled, prompt caching on the persona +
  books-snapshot system blocks, and a bounded agentic tool-use loop
  (`tally_status`, `list_ledgers`, `get_daybook`, `create_ledger`,
  `create_voucher`, `refresh_knowledge`). The provider layer is pluggable
  (`vm/app/lib/llm.js`) — other LLMs can be added behind the same interface.
- **Setup (one time)**: open the app → enter your Anthropic API key
  (console.anthropic.com) and choose a passcode. In Tally, enable the gateway:
  press F1 → Settings → Connectivity → "TallyPrime acts as" → **Both** (port
  9000). The app's header shows Tally connected/offline live.
- **Safety — enforced in code, not just prompt**: the model can only create
  **drafts** (`propose_entry`); posting happens exclusively when the user taps
  the Confirm button on the draft card. Posting is **idempotent** (a draft
  posts at most once; a marker check even survives a lost response),
  ledgers are verified/created first, debits=credits and date sanity are
  validated server-side, entries ≥ ₹1 lakh require typing the amount, and
  every posted voucher is **verified by reading it back** from the day book.
  Every action lands in an append-only audit log (`C:\TallyAI\data\audit.log`).
  Passcode + HttpOnly session cookie over HTTPS; config and history stay on
  the VM.
- **Document filing**: Tally can't store attachments, so bill photos are filed
  automatically on confirmation under
  `C:\TallyData\Documents\FY<yy-yy>\<MM-Month>\<date>_<label>_M-<id>.jpg`
  (covered by the nightly snapshots), and each voucher's narration carries its
  `[M-<id>]` code plus the document path — voucher→bill and bill→voucher are
  always traceable.
- **Operations**: deployed like everything else — synced from the assets
  bucket, converged by `repair.ps1` (npm install, self-signed cert, firewall
  rule, `TallyAIApp` scheduled task), restarted automatically only when its
  code changes, health-checked on port 8444.

## Self-healing and updates (how it stays foolproof)

External downloads move and fail — the design assumes it:

- All VM logic and content lives in [`vm/`](vm/) and is uploaded by Terraform
  to a **private S3 assets bucket in your account**. The VM re-syncs from it at
  **every boot**, then runs `repair.ps1` — an idempotent installer that checks
  each component by its real behavior (not just file presence) and reinstalls
  only what's missing, with retries and fallbacks.
- **Updating the fleet is just:** edit a file in `vm/` → `terraform apply`
  (uploads the change) → `./scripts/repair.sh` (or the next boot) applies it.
- The **TallyPrime installer URL is discovered live** from Tally's own site
  JavaScript (newest release wins), with last-known-good mirrors as fallback —
  a new Tally release can't break provisioning.
- A **weekly CI job** (`linkcheck.yml`) probes every external URL the project
  depends on and fails loudly when a vendor moves something — so the repo gets
  fixed before a user ever sees a dead link. Run it locally any time:
  `bash scripts/check-urls.sh`.
- On the VM, the non-technical path is two desktop buttons: **Check System
  Health** (PASS/FAIL for everything) → **Repair This Computer** (fixes it).

## Using your DSC (USB token) on the remote machine

Yes, a DSC works with a cloud machine — the token stays plugged into **your
local computer** and is *redirected* into the remote session. Three ways, pick
by what you connect from:

1. **From a Windows PC (most reliable):** connect with Remote Desktop, enable
   *Local Resources → Smart cards* in the connection settings, and the token
   appears on the remote machine automatically. This is standard practice for
   accountants using cloud VMs.
2. **From a Mac / via the browser:** smart-card redirection is unreliable on
   the Mac client and impossible in a browser tab, so the token travels over
   [VirtualHere](https://www.virtualhere.com/) USB-over-IP (server free for one
   device) through an **SSH reverse tunnel** — button `6 - Share DSC Token`
   automates it: VirtualHere server starts on the Mac, an SSH `-R` tunnel to
   the VM's built-in OpenSSH server (installed by `repair.ps1`, port 22 open
   only to your IP) carries port 7575, and the VM's VirtualHere client
   connects to `localhost:7575`. Free — no EasyFind subscription needed.
3. **Skip the DSC where the law allows:** GST and Income-tax accept
   Aadhaar-OTP e-verification (EVC) for proprietors and partnerships. A DSC is
   mainly mandatory for companies/LLPs (MCA filings) and some EPFO employer
   actions.

Practical routine: do everyday work in the browser; for the few minutes of
DSC-signing, connect via RDP from a Windows machine (or keep VirtualHere set
up). The token's driver must also be installed on the remote machine — one
click in the desktop "DSC Setup" folder, first time only.

## Good to know

- **If you can't connect**, your home IP probably changed: update `allowed_cidr`
  in `terraform.tfvars`, run `terraform apply`. (Or use AWS Console → Systems
  Manager → **Fleet Manager** → your instance → *Connect with Remote Desktop* —
  it works from anywhere, with no open ports.)
- **Restoring data**: every day at 2 AM IST a snapshot is taken (last 14 kept).
  To roll back, create a volume from a snapshot in the EC2 console and swap it in.
- **Never** run `terraform destroy` casually — it is the one command that deletes
  the machine and its disk. Termination protection also blocks accidental
  console/API terminations; snapshots survive even a destroy.
- **Tired of the IP changing every start?** If your domain's DNS is hosted on
  AWS Route 53, set two variables in `terraform.tfvars`:
  `dns_hostname = "tally.yourdomain.com"` and `dns_zone = "yourdomain.com"`,
  then `terraform apply`. The VM upserts that one A record with its current IP
  at every boot (and every repair), so `https://tally.yourdomain.com:8443`
  simply always works. IAM access is scoped to that single zone; your existing
  website/email records are untouched; costs nothing (no Elastic IP). The
  health check verifies the name stays current. (ADR-0018)
- **Three users out of the box**: every deployment gets `Administrator` (you),
  **`Accountant`** (Tally + documents read/write) and **`Auditor`** (documents
  read-only) — fenced non-admin users who connect over RDP; they can never read
  the AI app's API key, touch backups or change the system. `scripts/
  get-password.sh` (button `2`) prints all three passwords — share each role's
  password with the person taking that role. Recreated and enforced at every
  boot; disable with `create_default_users = false`. Extra users are your own
  call: `./scripts/add-vm-user.sh <Name> entry|review`. Add a matching named
  user inside Tally (F1 → Security) and the Edit Log attributes every voucher
  to them by name. Their networks must be in the firewall allowlist — fine
  while the machine runs on-demand; for always-on/multi-party operation see
  ADR-0019 (deliberately deferred).
- **Tally license** activates once and survives stop/start (same machine every time).
- **Tally edition & MCA compliance**: the staged installer defaults to
  **TallyPrime Edit Log** (always-on audit trail — required for Pvt Ltd/Ltd
  companies under MCA Companies (Accounts) Rules since Apr 2023; auditors
  report on it annually). Proprietorships/partnerships can set
  `tally_edition = "standard"` in `terraform.tfvars`. Same license, either
  build. The wider posture already fits the electronic-books rules: data on a
  server in India (Mumbai) with daily backups (nightly snapshots). Confirm
  specifics with your CA. (ADR-0014)
- Windows Server license cost is included in the EC2 hourly rate — nothing to buy.

## Sharing this setup

This repo is generic — anyone can use it in their own AWS account. The
zero-knowledge path on a Mac: get them the folder, have them double-click
**`0 - First Time Setup (run once)`** — it installs Homebrew/AWS CLI/Terraform,
walks them through entering AWS keys, and deploys with confirmation. The
manual path:

```bash
git clone <this-repo> && cd <repo>
cp terraform.tfvars.example terraform.tfvars   # set their own allowed_cidr
terraform init && terraform apply
```

**No git, no Mac, no local tools at all?** Two helpers:

- `./scripts/make-share-zip.sh` builds `TallyCloud-new.zip` on your Desktop —
  a clean, secret-free package you can email/WhatsApp to anyone. (With the
  `operator` argument it instead packages *your* deployment — state and key
  included — for a trusted person to operate the same machine.)
- The recipient can deploy **entirely in the browser** via AWS CloudShell:
  upload the zip there and run `bash scripts/cloudshell-deploy.sh`. No local
  installs of any kind; the USER-GUIDE has the click-by-click steps. All the
  `scripts/*.sh` helpers are Linux-compatible and work inside CloudShell too.

To *operate* an existing deployment from a second computer, copy the whole
folder (including `terraform.tfstate` and the `.pem` file) to it and run
button `0` there — it installs tools and links up without deploying anything.
Keep deploys (`terraform apply`, button `4`) on one "owner" machine to avoid
state conflicts; other devices can always start/stop via the AWS Console app.

State files, the `.pem` key, and `terraform.tfvars` are gitignored, so the repo
never contains anything account-specific or secret.

## Costs (Mumbai, approximate)

| Item | Cost |
|---|---|
| t3.large Windows, running | ~$0.14/hour → ~$1.50 for 10 h/month |
| 100 GB gp3 disk (always) | ~$9/month |
| Daily snapshots | < $1/month |
| **Total** | **~$10–12/month** |

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Please
read the design principles there first; the north star is that a
**non-technical accountant** must be able to use the result. Security issues:
see [SECURITY.md](SECURITY.md).

## License

Copyright 2026 Tally Cloud Workstation contributors.
Licensed under the [Apache License 2.0](LICENSE).

TallyPrime is a product of Tally Solutions Pvt. Ltd.; this project is not
affiliated with or endorsed by Tally Solutions, AWS, or any government portal
it references. You need your own TallyPrime license and AWS account.
