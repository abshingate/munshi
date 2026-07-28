# ADR-0021: Assisted data entry — the assistant fills, the human approves every submit

- **Status:** proposed
- **Date:** 2026-07-29

## Context

Compliance work is mostly transcription. A full day of TDS filing in July 2026
consisted almost entirely of reading a value from one place and typing it into
another: forty-odd fields into the RPU across three tabs, challan details into
e-Pay Tax, correction requests into TRACES, deductee rows into a return.

The operator's own description of the current loop: *"Right now I keep taking
screenshots and sharing with you and then you validate or correct yourself. I
need you to keep running the show and I will be the approver at specific
steps."*

That loop works but is slow and lossy. The assistant cannot see the screen, so
every state change costs a screenshot, a description, and a round trip. Errors
surface late — a wrong dropdown is discovered after it has been chosen, not
before.

Constraints that shape any solution:

- **Government portals prohibit automated access** in their terms, and defend
  it with OTP, DSC-on-token and captcha. Any design that tries to *submit*
  without a human is both a terms breach and, given the stakes of a wrong
  filing, reckless.
- **A wrong filing is expensive.** ₹200/day late fees, short-deduction
  demands, correction statements that need a conso file and another filing
  cycle. Speed is worth far less here than correctness.
- **Portals change without notice.** Mid-session on 28-07-2026 the OLTAS
  challan-correction facility moved between two portals and then went down for
  maintenance. Selector-based automation is inherently brittle against this.
- The VM already runs Chrome and a Node app with an LLM tool loop (ADR-0010),
  and the knowledge base holds the values to be entered (ADR-0020).

## Options considered

- **Keep the screenshot loop.** Zero build, zero risk, but the round-trip cost
  is the problem being solved.
- **Generate import files per tool** (e.g. the published ITD file format for
  Form 26Q/140). Excellent where a documented format exists — and it does for
  TDS returns, contrary to first assumption — but solves exactly one tool. The
  income-tax portal, TRACES and GST have no such path.
- **Full RPA that fills and submits.** Rejected outright: breaches portal
  terms, defeats OTP/DSC by design, and makes a mistake unreviewable because
  it has already happened.
- **Record-and-replay macros.** Brittle in the extreme against portals that
  reorganise, and encodes no understanding — a changed layout silently fills
  the wrong field.
- **Assistant-driven browser with mandatory human gates.** The assistant sees
  the page, decides what to fill, fills it, and then *stops*. The human
  reviews the filled form on screen and performs the submit action themselves.

## Decision

Build **assisted form filling**: a Playwright-driven Chromium on the VM that
the assistant can see and type into, with a hard stop before any irreversible
action.

Non-negotiable invariants:

1. **The assistant never submits.** Buttons that file, pay, confirm, or
   otherwise change state on a third-party system are never clicked by code.
   The human clicks them, on a screen showing the filled form.
2. **The human authenticates.** Login, OTP, DSC and captcha are always human
   actions. Credentials are never automated or stored by this component.
3. **Every fill is proposed, then applied.** The assistant states field, value
   and source ("₹3,000 — from tds-register.csv row 4, challan 26050700710083ICIC")
   before entering it, so a wrong value is caught before it is typed rather
   than after.
4. **Read before write, always.** The page is inspected and its actual fields
   enumerated before anything is entered — no assumptions about layout, which
   is what makes this survive portal changes that break recorded macros.
5. **Full audit trail.** Every action, value and screenshot is logged to the
   knowledge base, so what was entered and why is reconstructable later.
6. **Portal terms are respected.** The component assists a human who is
   present and in control; it does not create unattended sessions, does not
   poll, and does not scrape at machine speed.

### Surfaces

Compliance work is not only browser work. The same transcription problem
appears in desktop applications — the RPU, Tally screens the XML gateway
cannot reach, emSigner, DSC utilities, offline ITR utilities. The invariants
above are identical for all of them; only the mechanism differs.

**Preference order for any given task** — always take the highest available:

| # | Mechanism | Use when | Examples |
|---|---|---|---|
| 1 | **Documented API** | the vendor publishes one | Tally XML gateway (ADR-0010) |
| 2 | **Published file format** | an import/export spec exists | RPU: the ITD-prescribed `.txt` data structure, validated by the vendor's own FVU |
| 3 | **Accessibility layer** | a native app with no API or format | Windows UI Automation (`pywinauto` backend `uia`); **Java Swing additionally requires Java Access Bridge**, which is not enabled by default |
| 4 | **DOM automation** | web applications | Playwright over Chromium |
| 5 | **Coordinate clicking** | **never** | — |

Level 5 is excluded outright. Clicking fixed screen positions cannot verify
what it is typing into; a shifted layout silently enters a value in the wrong
field, which in a tax return is exactly the failure this system exists to
prevent.

Levels 3 and 4 share a rule that makes them tolerable: **enumerate the actual
controls and assert the target's identity before typing**. If the expected
field is not found, stop and ask — never fall back to guessing a position.

Scope for the first version, deliberately narrow: the **RPU** via its
published file format (level 2), and **form-filling on portals where the
human is already logged in** (level 4). Level 3 is added only where a real
task demands it, because accessibility support is uneven across applications
and must be verified per app rather than assumed.

### Feasibility, verified on the VM (29-07-2026)

Tested rather than assumed, because level 3 is the one that usually
disappoints:

| Capability | Result |
|---|---|
| .NET `UIAutomationClient` | **works**, no install needed |
| `WindowsAccessBridge-64.dll` | **present** (JRE 1.8.0_491 + System32 + SysWOW64) |
| `accessibility.properties` | **present and enabled** — Swing exposes its tree |
| `jabswitch.exe` | available, to toggle if it is ever disabled |

So the RPU's fields are reachable programmatically. Level 2 (its published
file format) remains preferred for building a return; level 3 is the fallback
for screens with no file path.

**Operational constraint discovered:** UI Automation from an SSM RunCommand
session sees zero top-level windows — SSM runs in a non-interactive window
station (session 0). Anything driving the desktop must run **in the
interactive session**, as a scheduled task with "run only when user is logged
on" or launched from the DCV desktop. This is a real deployment detail, not a
footnote: automation invoked the way every other component on this VM is
invoked will silently see an empty desktop.

## Consequences

- **The round trip collapses.** The assistant reads the live page instead of
  waiting for a screenshot, so a wrong dropdown is caught at the moment of
  filling.
- **The human stays the decision-maker at exactly the point that matters** —
  the irreversible one — which is also where the operator asked to be.
- **Brittleness is bounded, not eliminated.** Reading the page each time
  tolerates layout change far better than replaying recorded selectors, but a
  substantially redesigned portal will still require the assistant to
  re-orient. That is acceptable because a human is watching.
- **This is the highest-risk component in the system.** It types into
  government portals. Its invariants are not style preferences; a change that
  weakens gate 1 or 2 must be treated as a security change and reviewed as
  one.
- Chromium adds ~300 MB to the VM image and a dependency (Playwright) that
  must be kept current — accepted, since the alternative is a permanent
  screenshot loop.
- Where a documented import format exists, **prefer it over the GUI.** File
  generation validated by the vendor's own tool beats synthetic typing. UI
  filling is for systems that offer no such path.
