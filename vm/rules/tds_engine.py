#!/usr/bin/env python3
"""
TDS rules engine — deterministic computation from a cited rule set.

The model explains; this computes. Statutory values are never derived by a
language model, because they are rule-following (which code does perfectly)
rather than reasoning (which models do unreliably).

The motivating error, from real work in July 2026: the s.194I rent threshold
is ₹50,000 **per month**, not per year. Rent of ₹30,000/month is ₹3,60,000 a
year — over any annual reading of the limit, but comfortably under the actual
monthly one. TDS was deducted when none was due. A table encoding
`threshold_basis: per_month` cannot make that mistake.

Every answer carries the rule id and the authority it came from, so the
reasoning is checkable rather than trusted.

Usage
-----
    from tds_engine import TdsEngine
    eng = TdsEngine()

    eng.assess(rule_id="tds-rent-land-building", amount=30000, on_date=date(2026,5,7))
    eng.assess(rule_id="tds-professional-fees", amount=125000,
               on_date=date(2026,7,22), prior_year_total=25000)
    eng.interest(rule="int-late-deposit", amount=12500,
                 from_date=date(2025,11,7), to_date=date(2026,8,7))

Run directly for a self-test:  python3 tds_engine.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RULES_FILE = Path(__file__).parent / "tds-in.json"


@dataclass
class Assessment:
    """The outcome of applying one rule to one payment.

    `explanation` and `authority` exist so the result can be shown and
    checked, not merely trusted.
    """
    applies: bool
    tds: float
    rate: float | None
    rule_id: str
    label: str
    authority: str
    explanation: str
    requires_human: bool = False
    catch_up_on: float = 0.0          # earlier untaxed amounts now taxable
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        head = f"TDS {self.tds:,.2f}" if self.applies else "No TDS"
        return f"{head} — {self.explanation}"


class TdsEngine:
    def __init__(self, rules_file: Path | str = RULES_FILE):
        self.data = json.loads(Path(rules_file).read_text(encoding="utf-8"))
        self.rules = {r["id"]: r for r in self.data["rules"]}
        self.interest_rules = {r["id"]: r for r in self.data["interest_and_penalties"]}

    # -- rule lookup ---------------------------------------------------------

    def rule_for(self, rule_id: str, on_date: date | None = None) -> dict:
        """Fetch a rule, checking it was in force on the given date.

        Rules are effective-dated because compliance questions are almost
        always about a past period, and a rule that changed in between would
        otherwise give a confidently wrong answer.
        """
        r = self.rules.get(rule_id)
        if not r:
            raise KeyError(
                f"Unknown rule '{rule_id}'. Known: {', '.join(sorted(self.rules))}"
            )
        if on_date:
            start = date.fromisoformat(r["applies_from"])
            if on_date < start:
                raise ValueError(
                    f"Rule '{rule_id}' applies from {start}, but the date given is "
                    f"{on_date}. Add the rule version that was in force then — do "
                    f"not assume the current one applied."
                )
            if r.get("applies_to"):
                end = date.fromisoformat(r["applies_to"])
                if on_date > end:
                    raise ValueError(
                        f"Rule '{rule_id}' ceased on {end}; date given is {on_date}."
                    )
        return r

    # -- the main question ---------------------------------------------------

    def assess(
        self,
        rule_id: str,
        amount: float,
        on_date: date | None = None,
        prior_year_total: float = 0.0,
        single_payment: float | None = None,
    ) -> Assessment:
        """Decide whether TDS applies to one payment, and how much.

        amount            this payment, excluding GST
        prior_year_total  what has already been paid to this party this FY
                          under this section (drives aggregate thresholds)
        single_payment    for the 194C dual test, the largest single invoice
        """
        r = self.rule_for(rule_id, on_date)
        auth = r.get("authority", "")
        label = r.get("label", rule_id)
        warnings: list[str] = []

        # Some payments must never be computed automatically.
        if r.get("requires_human"):
            return Assessment(
                applies=False, tds=0.0, rate=None, rule_id=rule_id, label=label,
                authority=auth, requires_human=True,
                explanation=(f"{label}: requires a human decision. "
                             f"{r.get('notes', '')}").strip(),
            )

        if r["rate_type"] == "slab":
            return Assessment(
                applies=True, tds=0.0, rate=None, rule_id=rule_id, label=label,
                authority=auth, requires_human=True,
                explanation=(f"{label} is computed at slab rates on estimated annual "
                             f"income, not as a flat percentage. Use the payroll "
                             f"schedule, not this function."),
            )

        rate = float(r["rate"])
        basis = r.get("threshold_basis")
        threshold = r.get("threshold")

        # --- threshold test, which differs materially by basis --------------
        applies = False
        reason = ""
        catch_up = 0.0

        if basis == "no_threshold":
            applies = True
            reason = "no threshold — applies from the first rupee"

        elif basis == "per_month":
            # THE critical case. The limit is monthly, so an annual total is
            # irrelevant and must not be compared against it.
            applies = amount > threshold
            if applies:
                reason = (f"this month's payment {amount:,.2f} exceeds the "
                          f"per-MONTH threshold of {threshold:,.0f}")
            else:
                reason = (f"this month's payment {amount:,.2f} is at or below the "
                          f"per-MONTH threshold of {threshold:,.0f} "
                          f"(annualised {amount * 12:,.0f} is NOT the test)")

        elif basis == "per_invoice_or_annual_aggregate":
            # 194C dual test: either trigger is sufficient.
            single = single_payment if single_payment is not None else amount
            annual_cap = r.get("threshold_secondary")
            new_total = prior_year_total + amount
            by_single = single > threshold
            by_annual = new_total > annual_cap
            applies = by_single or by_annual
            if by_single and by_annual:
                reason = (f"single payment {single:,.2f} exceeds {threshold:,.0f} "
                          f"AND year total {new_total:,.2f} exceeds {annual_cap:,.0f}")
            elif by_single:
                reason = f"single payment {single:,.2f} exceeds {threshold:,.0f}"
            elif by_annual:
                reason = (f"year total {new_total:,.2f} exceeds the aggregate "
                          f"limit of {annual_cap:,.0f}")
            else:
                reason = (f"single payment {single:,.2f} is within {threshold:,.0f} "
                          f"and year total {new_total:,.2f} is within {annual_cap:,.0f}")
            if by_annual and prior_year_total > 0:
                catch_up = prior_year_total

        elif basis in ("per_year_per_vendor", "per_year_per_payee"):
            new_total = prior_year_total + amount
            applies = new_total > threshold
            if applies:
                reason = (f"year-to-date total {new_total:,.2f} exceeds the annual "
                          f"threshold of {threshold:,.0f}")
                if prior_year_total > 0 and prior_year_total <= threshold:
                    catch_up = prior_year_total
            else:
                reason = (f"year-to-date total {new_total:,.2f} is at or below the "
                          f"annual threshold of {threshold:,.0f}")

        else:
            raise ValueError(f"Rule '{rule_id}' has unhandled threshold_basis {basis!r}")

        # --- preconditions --------------------------------------------------
        if r.get("precondition"):
            warnings.append(
                f"Precondition not verified by this engine: {r['precondition']}. "
                f"Confirm it holds before relying on this result."
            )

        if not applies:
            return Assessment(
                applies=False, tds=0.0, rate=rate, rule_id=rule_id, label=label,
                authority=auth, warnings=warnings,
                explanation=f"{label}: no TDS — {reason}.",
            )

        # --- amount on which TDS is computed --------------------------------
        effect = r.get("threshold_effect", "whole_amount")
        if effect == "excess_only":
            base = max(0.0, (prior_year_total + amount) - threshold)
            base = min(base, amount)
            base_note = f"on the excess over {threshold:,.0f}"
        elif effect == "whole_aggregate" and catch_up:
            base = amount + catch_up
            base_note = (f"on {amount:,.2f} plus catch-up on {catch_up:,.2f} "
                         f"of earlier untaxed payments")
        else:
            base = amount
            base_note = f"on {amount:,.2f}"

        tds = round(base * rate / 100.0, 2)

        return Assessment(
            applies=True, tds=tds, rate=rate, rule_id=rule_id, label=label,
            authority=auth, catch_up_on=catch_up, warnings=warnings,
            explanation=(f"{label}: TDS at {rate}% {base_note} = {tds:,.2f} "
                         f"— {reason}."),
        )

    # -- interest ------------------------------------------------------------

    def interest(self, rule: str, amount: float, from_date: date, to_date: date) -> dict:
        """Interest under s.201(1A). A PART month counts as a FULL month —
        the most commonly miscalculated part of this, so it is explicit."""
        r = self.interest_rules.get(rule)
        if not r:
            raise KeyError(f"Unknown interest rule '{rule}'")
        if to_date < from_date:
            raise ValueError("to_date is before from_date")

        months = (to_date.year - from_date.year) * 12 + (to_date.month - from_date.month)
        if to_date.day > from_date.day:
            months += 1
        months = max(1, months)          # any delay is at least one month

        pct = float(r["rate_percent_per_month"])
        interest = round(amount * pct / 100.0 * months, 2)
        return {
            "interest": interest,
            "months": months,
            "rate_percent_per_month": pct,
            "authority": r["authority"],
            "explanation": (f"{months} month(s) at {pct}% per month on {amount:,.2f} "
                            f"= {interest:,.2f} (part month counts as full)"),
        }

    def late_fee(self, days_late: int, tds_in_statement: float) -> dict:
        """s.234E late filing fee, capped at the TDS in that statement."""
        r = self.interest_rules["fee-late-return"]
        raw = days_late * float(r["amount_per_day"])
        fee = min(raw, tds_in_statement)
        return {
            "fee": round(fee, 2),
            "uncapped": round(raw, 2),
            "capped": raw > tds_in_statement,
            "authority": r["authority"],
            "explanation": (f"{days_late} days x 200 = {raw:,.2f}"
                            + (f", capped at the statement's TDS of {tds_in_statement:,.2f}"
                               if raw > tds_in_statement else "")),
        }


# ---------------------------------------------------------------------------
# Self-test: every case below is drawn from real work, not invented.
# ---------------------------------------------------------------------------

def _selftest() -> int:
    eng = TdsEngine()
    failures = 0

    def check(name, got, want):
        nonlocal failures
        ok = abs(got - want) < 0.01
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got:,.2f}, want {want:,.2f}")
        if not ok:
            failures += 1

    print("Rent, Bharti Palkar — the error this engine exists to prevent:")
    a = eng.assess("tds-rent-land-building", 30000, date(2026, 5, 7))
    check("30,000/month rent -> no TDS", a.tds, 0.0)
    print(f"        {a.explanation}")

    a = eng.assess("tds-rent-land-building", 55000, date(2026, 5, 7))
    check("55,000/month rent -> 5,500", a.tds, 5500.0)

    print("\nARTH audit fee, 194J:")
    a = eng.assess("tds-professional-fees", 125000, date(2026, 7, 22))
    check("1,25,000 fee -> 12,500", a.tds, 12500.0)

    print("\nDipti Thite, below threshold then crossing it:")
    a = eng.assess("tds-professional-fees", 25000, date(2026, 6, 1))
    check("25,000 alone -> no TDS", a.tds, 0.0)
    a = eng.assess("tds-professional-fees", 30000, date(2026, 7, 1), prior_year_total=25000)
    check("30,000 after 25,000 -> 5,500 incl catch-up", a.tds, 5500.0)
    print(f"        {a.explanation}")

    print("\nDirector fees — no threshold:")
    a = eng.assess("tds-director-fees", 5000, date(2026, 5, 1))
    check("5,000 director fee -> 500", a.tds, 500.0)

    print("\n194C dual test:")
    a = eng.assess("tds-contractor-company", 31000, date(2026, 5, 1))
    check("single 31,000 -> 620 (single-payment trigger)", a.tds, 620.0)
    a = eng.assess("tds-contractor-company", 20000, date(2026, 5, 1))
    check("single 20,000, no history -> no TDS", a.tds, 0.0)

    print("\nNon-resident must refuse:")
    a = eng.assess("tds-non-resident", 100000, date(2026, 5, 1))
    print(f"  {'PASS' if a.requires_human else 'FAIL'}  s.195 flagged for human")
    if not a.requires_human:
        failures += 1

    print("\nInterest on the ARTH FY25-26 default (Nov 2025 -> Aug 2026):")
    i = eng.interest("int-late-deposit", 12500, date(2025, 11, 7), date(2026, 8, 7))
    check("9 months at 1.5% on 12,500", i["interest"], 1687.5)
    print(f"        {i['explanation']}")

    print("\nLate fee cap:")
    f = eng.late_fee(103, 3000)
    check("103 days on a 3,000 statement -> capped at 3,000", f["fee"], 3000.0)

    print("\nEffective-dating refuses out-of-period questions:")
    try:
        eng.assess("tds-rent-land-building", 30000, date(2020, 5, 7))
        print("  FAIL  should have refused a 2020 date")
        failures += 1
    except ValueError:
        print("  PASS  refused a date before the rule took effect")

    print("\n" + ("ALL PASS" if not failures else f"{failures} FAILURE(S)"))
    return failures


if __name__ == "__main__":
    raise SystemExit(_selftest())
