# ADR-0003: Amazon DCV for browser access, RDP + Fleet Manager as fallbacks

- **Status:** accepted
- **Date:** 2026-07-26

## Context

The user wanted browser access ("else I can remote login"). Windows remote
access options vary wildly in cost, quality, and setup burden for a
non-technical user.

## Options considered

- **RDP only** — needs a client app; fine on Windows, mediocre on Mac, no
  browser story.
- **Apache Guacamole** — browser RDP, but requires running and maintaining a
  gateway service ourselves.
- **Third-party (TeamViewer/AnyDesk)** — licensing cost, third-party trust.
- **Amazon DCV** — AWS's own remote desktop; license is free on EC2 (verified
  via an instance-role read of the regional license bucket), full browser
  client on 8443, silent-installable MSI with a stable "latest" URL.

## Decision

Amazon DCV as the primary access path, with three-deep fallback: DCV browser →
native RDP → SSM Fleet Manager (works with zero open ports even when the
user's IP changed).

## Consequences

- Every access path has a fallback (invariant #5).
- Self-signed cert means a one-time browser warning — accepted and documented
  in plain language rather than buying/renewing certificates for a
  changing-IP host.
- The DCV display sizes itself to the browser window; anything rendering to
  the screen (e.g. the info wallpaper) must handle non-1080p resolutions —
  this bit us once (wallpaper cropped) and is now handled by rendering at the
  actual resolution.
