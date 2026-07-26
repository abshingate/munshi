# ADR-0007: Multi-layer resilience for external download URLs

- **Status:** accepted
- **Date:** 2026-07-26

## Context

Two vendor URLs died in the project's first week: Tally's installer URL had
to be extracted from their site's JavaScript (their download button is
dynamic, no stable link exists), and VirtualHere moved their server download
(discovered mid-automation). Every bootstrap dependency is a URL some vendor
can move without notice.

## Options considered

- **Mirror the binaries in our S3 bucket** — immune to vendor moves, but we'd
  be redistributing third-party software (licensing risk) and serving stale,
  unpatched versions.
- **Pin exact versioned URLs** — breaks on every vendor release.
- **Layered live resilience** — discover, retry, fall back, and alarm.

## Decision

Four layers: (1) dynamic discovery where possible — the TallyPrime URL is
parsed from Tally's own `DownloadUtility` JS at repair time, newest release
first; (2) retries + multi-URL fallbacks + size validation in `Get-File`;
(3) last-resort UX — a desktop shortcut to the vendor's download page, so a
human can always finish manually; (4) a weekly CI job (`linkcheck.yml` /
`scripts/check-urls.sh`) that probes every external URL and emails the
maintainer when one dies — fix the repo before a user ever hits it.

## Consequences

- Rule: **any new external URL added anywhere must also be added to
  `scripts/check-urls.sh`** (recorded in ARCHITECTURE.md).
- A new Tally release (e.g. Rel8.0) requires no code change; a moved JS
  endpoint still alarms within a week.
- We accept up to ~a week of a silently dead low-traffic URL between cron
  runs; repair's boot-time retry narrows the real user impact.
