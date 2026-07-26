# ADR-0010: AI Accountant — Node + official Anthropic SDK + Tally XML gateway, pluggable provider

- **Status:** accepted
- **Date:** 2026-07-26

## Context

Requirement: a chat AI accountant on the VM — mobile-first, reads/writes
Tally, understands bill photos, "plug in any LLM but start with Claude",
usable by a non-accountant.

## Options considered

- **Integration channel to Tally:** UI automation (brittle, breaks per Tally
  release) vs ODBC (read-only) vs the **XML gateway on port 9000** — Tally's
  own supported API, reads and writes, already local.
- **App stack:** a framework-heavy app (Express/React — more deps to keep
  healthy on an unattended VM) vs **zero-framework Node** (http/https/fs
  built-ins) with exactly one dependency, the official `@anthropic-ai/sdk`
  (raw HTTP to the API was rejected — the SDK gives typed errors, retries,
  and tracks API evolution).
- **Model/loop:** `claude-opus-5` (vision + strong agentic tool use; server-
  side refusal fallbacks enabled) driving a **manual tool-use loop** — chosen
  over the beta tool runner because the server owns a persistent multi-turn
  conversation with custom gating (and later, ADR-0011's draft flow).
- **Exposure:** on-VM only vs **HTTPS on 8444 restricted to allowed_cidr** —
  the phone on home Wi-Fi shares the home IP, so mobile access needs no new
  auth infrastructure beyond the app's passcode.

## Decision

Zero-framework Node app (`vm/app/`), official Anthropic SDK behind a
provider interface (`lib/llm.js` — `chat({system, messages, tools})`),
Tally XML gateway client (`lib/tally.js`), knowledge snapshot injected as a
cache-controlled system block, passcode + HMAC session cookie, deployed and
converged like every other VM component (ADR-0005).

## Consequences

- Adding an LLM = one provider file; adding a Tally operation = one tool +
  one XML template. Both are deliberately narrow seams.
- The gateway requires a one-time manual toggle in Tally's UI ("acts as:
  Both") — surfaced in the app header as connected/offline rather than hidden.
- API key and chat history live only on the VM; costs are the owner's API
  usage, kept down by prompt caching.
- Restart-on-code-change only (file hash), so repairs never drop a chat.
