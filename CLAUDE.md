# Claude session briefing — Munshi / Tally Cloud Workstation

This repo deploys and operates a cloud Windows workstation running TallyPrime
(the company's books) plus the Munshi AI-accountant app. Sessions here are
routinely asked to operate the VM and read/write Tally through its XML
gateway. This file tells you how.

## The VM

- EC2 Windows instance, tag `Name=tally-workstation`, found via the AWS CLI
  (credentials are configured on this machine). Usually **stopped** — start it
  when needed, it auto-stops after ~1h idle.
- `./scripts/status.sh` · `./scripts/start.sh` · `./scripts/stop.sh` ·
  `./scripts/get-password.sh` (all user passwords) · `./scripts/fix-ip.sh`
  (refresh the owner-IP allowlist if 8443 is unreachable).
- User-facing address: the `dns_hostname` in terraform.tfvars (stable across
  restarts). Browser desktop: `https://<hostname>:8443` (DCV, Administrator).
- Run commands on the VM via SSM `AWS-RunPowerShellScript`. Notes learned the
  hard way:
  - Build `--parameters` as a JSON file via a python heredoc (inline JSON
    with newlines breaks the CLI).
  - `Read-S3Object`/AWS cmdlets work (instance role is **read-only** on the
    assets bucket — no uploads from the VM; bring large outputs back as
    gzip+base64 in command output, chunked if >24KB).
  - First AWSPowerShell module load in a session takes ~30–60s.

## Tally XML gateway

- TallyPrime serves XML on `http://localhost:9000` **on the VM, only while
  the desktop app is open with a company loaded** — the user must open Tally
  and log in (security is enabled); ask them, then POST XML via SSM.
- One company loaded at a time avoids name ambiguity. The live company is
  `C:\TallyData\050503`. Never load a reference copy as if it were live.
- Reads: prefer built-in report exports (`ID` = report name e.g. `Trial
  Balance`) over large custom collections — a heavy collection can wedge
  Tally and abandoned requests keep processing (if the gateway stops
  answering, ask the user to Esc/restart Tally).
- Writes (`Import Data` / voucher `Create`): debit = negative `AMOUNT` +
  `ISDEEMEDPOSITIVE Yes`; credit = positive + `No`. Voucher dates must fall
  inside the company's active period. **Always show the user the proposed
  entries and get explicit confirmation before writing; verify after writing
  by re-reading (day book or trial balance).** Include a `[M-...]` marker in
  narrations for traceability.
- Sign convention in exports: debit balances positive, credit negative.

## Hard rules

- Never enable TallyVault. Never "Split Company Data". Don't alter the
  company's "Financial year beginning from".
- The books are Edit-Logged (MCA audit trail) — corrections are new vouchers,
  never silent edits/deletes.
- `local/` and `terraform.tfvars` are gitignored and must stay out of git
  (company data, operator values). The repo is public.
- FY 2025-26 is closed and reconciled to the signed financial statements
  (backup `050503-FINAL-FY2526-CLOSED-2026-07-27.zip` in `C:\TallyData\Backups`).
  Post FY 2026-27 work in period 01-04-2026 → 31-03-2027.

## Code map

- `vm/app/lib/tally.js` — gateway client used by the Munshi app (on the VM).
- `vm/app/lib/recon.js` — bank↔books reconciliation engine.
- `vm/app/lib/fsgen.js` — Schedule III financial-statements generator
  (`docs/fs-generator.md`); company config + fixtures live in `local/fsgen/`.
- `analysis/` — FY25-26 forensic analysis notes. `docs/decisions/` — ADRs;
  record notable design decisions as new ADRs as they're made.
