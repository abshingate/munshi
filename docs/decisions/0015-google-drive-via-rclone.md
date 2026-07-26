# ADR-0015: Google Drive sync via rclone (official Drive client unsupported on Windows Server)

- **Status:** accepted
- **Date:** 2026-07-26

## Context

The user wanted Google Drive on the VM for easy file sharing between their
devices and the machine (e.g. receiving the CA's Tally backup, bills,
statements). Empirically verified during rollout: **Google Drive for Desktop
does not support Windows Server** — the official installer (direct and via
Chocolatey) exits silently with nothing installed on Server 2022.

## Options considered

- **Official Drive client** — ruled out by the OS itself; hacks (OS-version
  spoofing, ancient client versions) are exactly the fragility we avoid.
- **Browser-only** (drive.google.com in Chrome) — works with zero setup and
  remains the documented fallback, but no synced folder, so no
  "drop a file on your phone, it appears on the VM" flow.
- **rclone bisync** — the standard open-source sync tool; server-friendly,
  choco-installable (self-healed like everything else), OAuth once.

## Decision

rclone installs via the repair loop. A one-time desktop button ("Set up
Google Drive") runs the interactive Google sign-in, does the initial
`bisync --resync`, and registers a SYSTEM scheduled task syncing
`C:\TallyData\Drive` ↔ the `TallyCloud` folder in the user's Drive every 5
minutes, two-way. rclone's config lives at `C:\ProgramData\rclone\rclone.conf`
(machine location, so the SYSTEM task and the interactive user share it).

## Consequences

- The synced folder sits inside `C:\TallyData` — nightly snapshots cover it,
  and it's an easy inbox for CA backups and bills.
- Sync is scoped to one dedicated Drive folder (`TallyCloud`), not the whole
  Drive — bounded storage/bandwidth and no accidental exposure of the user's
  entire Drive on a shared machine.
- 5-minute cadence, not instant; browser Drive remains available for
  anything urgent. bisync conflicts create suffixed copies rather than
  losing data.
- The OAuth token in rclone.conf grants Drive access — same trust level as
  the signed-in browser session on this single-user machine; revocable from
  the user's Google account security page.
