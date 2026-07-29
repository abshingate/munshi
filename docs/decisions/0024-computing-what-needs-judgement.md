# ADR-0024: Computing depreciation, notes and tax — and where the line really is

- **Status:** accepted
- **Date:** 2026-07-29
- **Related:** ADR-0023 (draft financial statements)

## Context

ADR-0023 excluded depreciation, provisions, tax and notes from the generated
statements on the grounds that they "need a CA". The user challenged that:

> *"why cant we do this ... those need the CA ???"*

The challenge was correct. Five genuinely different things had been collapsed
into one exclusion, and the real reason for excluding most of them was that
they are **harder**, not that they require professional judgement. That is a
bad reason, and dressing it up as a professional boundary made it worse — it
presents a capability gap as a principle.

## Decision

Separate the work by what it actually requires, and build everything on the
computable side.

### Computable — now built

| Area | Why it is computation, not judgement |
|---|---|
| **Depreciation** | Schedule II useful lives are *published law*. Tally holds dated acquisition vouchers, so pro-rata charges on additions are arithmetic. |
| **Notes to accounts** | Most Schedule III notes are prescribed *disaggregation tables* filled from ledger data. |
| **Current tax** | Book profit → statutory disallowances → rate. The rates are law. |
| **Regime comparison** | Normal vs s.115BAA vs MAT is pure modelling, and the answer is often counter-intuitive. |

### Genuinely needs a human — and now says exactly why

| Area | The judgement involved |
|---|---|
| Deferred tax | Whether future taxable profit is *probable* enough to recognise a DTA |
| Contingent liabilities | By definition **not booked** — no ledger holds them |
| Doubtful debts | Whether a debt is recoverable |
| Gratuity / leave encashment | Actuarial valuation |
| Going concern, impairment | Assessment of the future |
| MSMED disclosure | Each vendor's Udyam registration status |
| Related party list | Management representation |
| **The audit opinion** | s.143 requires an independent CA. Full stop. |

### The rule that separates them

> **If the input is law or ledger data, compute it. If the input is a belief
> about the future or a fact only management holds, ask for it — and leave the
> space visibly blank rather than filling it with a plausible number.**

A blank that says *"needs actuarial valuation"* is safe. A number that looks
computed but rests on a guessed useful life is dangerous, because it will
balance, look reasonable, and be wrong.

## Design constraints adopted

1. **Never default a classification.** An asset whose Schedule II class cannot
   be determined from its ledger name is reported as **UNCLASSIFIED**, not
   assigned a default life. A wrong life produces a wrong charge that still
   looks reasonable — the worst kind of error.

2. **Always show the working.** Every depreciation charge prints its
   derivation: cost, date, life, rate, days held, the pro-rata fraction, and
   any residual-value cap. A figure that cannot be checked by hand is not
   evidence.

3. **Compare against what was booked.** The register computes the Schedule II
   charge *and* reports what Tally actually booked, with the difference. The
   comparison is the point: ₹7,03,508 was booked in FY2025-26 and had never
   been verified.

4. **Rates carry a verification date and a warning.** `schedule2.json` and
   `tax_rates.json` both record `_verified_on` and instruct re-verification
   before any filing. Corporate rates change with each Finance Act; a stale
   rate card is a silent error.

5. **Derived rates are verified by test, not by trust.** Schedule II gives
   *lives*, not rates. The WDV rates are derived as `1 - residual^(1/life)`
   and a test recomputes all of them. Likewise the 115BAA effective rate must
   come out at 25.168%.

## Two findings this surfaced immediately

- **s.115BAA forfeits carried-forward losses and MAT credit, irrevocably.**
  This company has four loss years. Electing 115BAA on a single year's
  comparison could be an expensive mistake, so the output refuses to
  recommend it without a multi-year warning.

- **s.79 restriction.** A closely-held company loses carried-forward losses if
  beneficial shareholding carrying 51% of voting power changes. This company
  did a **₹43,72,706 buyback in FY2021-22**. Whether that triggered s.79 needs
  checking before any loss is claimed.

Neither was found by looking for it; both fell out of writing the rate cards
honestly.

## Consequences

**Good.** The company gets a Fixed Asset Register, full notes, and a tax
computation with regime comparison — none of which existed. The CA receives
drafts to check rather than blanks to fill.

**Risk.** A computed number carries more authority than a blank. Mitigated by
showing every working, flagging every unclassified item, and comparing against
what was booked — but the covering note must keep saying these are drafts.

**Honest limit.** This reduces preparation effort and catches errors early. It
does not reduce the audit, and nothing here substitutes for the auditor's
judgement on the items listed above.
