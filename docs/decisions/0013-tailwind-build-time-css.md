# ADR-0013: Tailwind CSS via a build-time compiled stylesheet, committed to the repo

- **Status:** accepted
- **Date:** 2026-07-26

## Context

The AI Accountant UI should look professional and follow modern practice:
mobile-first, consistent design system, proper feedback states. Tailwind was
requested. The app is served from the VM and used from phones; the project's
resilience principles (ADR-0007) discourage external runtime dependencies.

## Options considered

- **Tailwind Play CDN (`<script src="cdn.tailwindcss.com">`)** — one line,
  but explicitly not for production: ships the whole JIT compiler to every
  page load, and makes the page depend on a third-party CDN being reachable —
  the exact class of fragility ADR-0007 exists to eliminate.
- **Runtime build on the VM** — adds Tailwind + build tooling to the VM's npm
  install and a failure mode ("app down because CSS build failed") for zero
  user benefit.
- **Build-time compilation, artifact committed** — `npm run build:css`
  (Tailwind v4 CLI, devDependency) compiles a minified stylesheet containing
  only the classes actually used (~22KB); `public/tailwind.css` is committed
  and served by the VM like any static file.

## Decision

Build-time Tailwind. Brand tokens (`--color-navy`, `--color-gold`) live in
`tailwind.input.css` via `@theme`. Contributors who touch UI classes rerun
`npm run build:css` and commit the artifact. `node_modules` is excluded from
git and from the Terraform S3 upload (the VM installs runtime deps itself,
and dev deps never leave the workstation).

## Consequences

- The VM serves one static CSS file — no CDN, no runtime compiler, no new
  failure modes; page works fully offline from the VM's perspective.
- Committing a generated artifact is unusual but deliberate: it keeps the VM
  and CI free of a Node build step. The cost is remembering to rebuild —
  mitigated by the npm script and a CONTRIBUTING note; if UI work becomes
  frequent, add a CI check that the artifact matches the source.
- UX conventions set alongside this: browser `prompt()`/`confirm()` replaced
  with proper modals/bottom sheets, toasts for operation feedback, explicit
  loading/disabled states — these are now the bar for future UI work.
