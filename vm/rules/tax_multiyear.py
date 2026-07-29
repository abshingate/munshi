#!/usr/bin/env python3
"""
Multi-year tax computation with loss carry-forward that actually chains.

Running ten single-year computations independently is WRONG: each restarts
with nil brought-forward loss, so every profitable year is over-taxed. This
runs the years in sequence, carries each year's loss forward, applies the
**eight-year limit under s.72**, and lets losses expire when they should.

Also produces `notes.py` output for every year in the same pass.

WHAT IT ASSUMES — and these are assumptions, not facts
------------------------------------------------------
1. **Losses arise as computed from the books.** The real figures come from
   filed returns and assessment orders, which may differ. Book loss is not
   assessed loss.
2. **The whole loss is business loss.** In reality some is *unabsorbed
   depreciation* under s.32(2), which carries forward INDEFINITELY and is not
   subject to s.79. The split matters and must come from the returns.
3. **Returns were filed on time.** A business loss cannot be carried forward
   at all if the return for the loss year missed the s.139(1) due date.
4. **s.79 was not triggered.** The FY2021-22 buyback is unresolved — see
   S79-BUYBACK-ANALYSIS.md. If it was triggered, pre-2021-22 losses vanish.

The output states all four, and models the s.79 scenario separately so the
exposure is visible rather than assumed away.

Usage
-----
    python tax_multiyear.py --out C:\\TallyData\\Drive\\For-CA\\draft-financials
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tax_computation import compute, rupees, load_rates, tax_under, surcharge_rate  # noqa: E402

YEARS = ["2016-17", "2017-18", "2018-19", "2019-20", "2020-21",
         "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]

CARRY_FORWARD_YEARS = 8   # s.72
BUYBACK_FY = "2021-22"


def run_chain(years: list[str], apply_s79: bool = False) -> list[dict]:
    """Compute each year in sequence, carrying losses forward.

    Losses are held as (fy, amount) so the eight-year limit can expire them
    individually — a single running total cannot do that correctly.
    """
    pool: list[list] = []   # [fy_index, remaining_amount]
    results = []

    for idx, fy in enumerate(years):
        # s.79: a change in beneficial shareholding wipes losses incurred in
        # years BEFORE the change. Model it by emptying the pool at that year.
        if apply_s79 and fy == BUYBACK_FY:
            wiped = sum(p[1] for p in pool)
            pool = []
        else:
            wiped = 0.0

        # Expire anything older than eight years (s.72).
        expired = sum(p[1] for p in pool if idx - p[0] > CARRY_FORWARD_YEARS)
        pool = [p for p in pool if idx - p[0] <= CARRY_FORWARD_YEARS]

        available = sum(p[1] for p in pool)
        res = compute(fy, bf_loss=available, bf_deprec=0.0)

        # Consume the pool oldest-first, which is how set-off works.
        used = res["loss_used"]
        remaining_to_use = used
        for p in sorted(pool, key=lambda x: x[0]):
            if remaining_to_use <= 0:
                break
            take = min(p[1], remaining_to_use)
            p[1] -= take
            remaining_to_use -= take
        pool = [p for p in pool if p[1] > 0.005]

        # This year's own loss (if any) joins the pool.
        gti = res["gross_total_income"]
        if gti < 0:
            pool.append([idx, -gti])

        res["_available"] = available
        res["_expired"] = expired
        res["_wiped_by_s79"] = wiped
        res["_closing_pool"] = sum(p[1] for p in pool)
        results.append(res)

    return results


def render(chain: list[dict], chain_s79: list[dict], company: str) -> str:
    out = []
    A = out.append

    A(f"# {company.split(' - (')[0]}")
    A("")
    A("## Ten-year tax computation with loss carry-forward")
    A("")
    A("> ### ⚠️ DRAFT — assumptions stated below are doing real work")
    A("> Losses are chained year to year with the **eight-year limit under")
    A("> s.72** applied. This is *not* ten independent computations — running")
    A("> them separately would restart every year with nil brought-forward")
    A("> loss and over-tax every profitable year.")
    A("")
    A(f"*Generated {date.today().strftime('%d %B %Y')}. Figures in ₹.*")
    A("")

    # ---- the chain ----
    A("## Year by year")
    A("")
    A("| FY | Book profit/(loss) | Add-backs | Gross total income | "
      "B/f loss available | Set off | **Total income** | Tax ₹ | C/f loss |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in chain:
        reg = next(iter(r["regimes"].values()), None)
        tax = reg["tax"]["total"] if reg else 0.0
        mat = r["mat"]["total"]
        liab = max(tax, mat) if r["total_income"] > 0 else 0.0
        A(f"| {r['fy']} | {rupees(r['book_profit'])} "
          f"| {rupees(r['total_adds'])} | {rupees(r['gross_total_income'])} "
          f"| {rupees(r['_available'])} | {rupees(r['loss_used'])} "
          f"| **{rupees(r['total_income'])}** | {rupees(liab)} "
          f"| {rupees(r['_closing_pool'])} |")
    A("")

    A("> **The tax shown for FY2016-17 to FY2019-20 is a RECOMPUTATION, not")
    A("> what was paid.** Those years are assessed and closed; their returns")
    A("> are the authority. The figures are here only to show the shape of the")
    A("> decade and to check nothing is obviously inconsistent — do not treat")
    A("> a difference against the filed returns as a liability without")
    A("> establishing why it differs. The years that matter for action are")
    A("> **FY2024-25 onward**.")
    A("")

    expired_total = sum(r["_expired"] for r in chain)
    if expired_total > 0.005:
        A(f"⚠️ **{rupees(expired_total)} of loss expired unused** under the")
        A("eight-year limit in s.72. Once expired it cannot be revived.")
        A("")

    final = chain[-1]
    A(f"**Loss carried forward at 31 March 2026: {rupees(final['_closing_pool'])}**")
    A("")

    # ---- s.79 scenario ----
    A("## If s.79 was triggered by the FY2021-22 buyback")
    A("")
    A("The buyback is unresolved — see `S79-BUYBACK-ANALYSIS.md`. On the")
    A("evidence available it probably was **not** triggered, but the exposure")
    A("is worth seeing:")
    A("")
    A("| | Losses survive (likely) | s.79 triggered |")
    A("|---|---:|---:|")
    A(f"| Loss carried forward at 31-03-2026 "
      f"| {rupees(final['_closing_pool'])} "
      f"| {rupees(chain_s79[-1]['_closing_pool'])} |")
    tax_a = sum(max(next(iter(r['regimes'].values()))['tax']['total'],
                    r['mat']['total']) if r['total_income'] > 0 else 0.0
                for r in chain)
    tax_b = sum(max(next(iter(r['regimes'].values()))['tax']['total'],
                    r['mat']['total']) if r['total_income'] > 0 else 0.0
                for r in chain_s79)
    A(f"| Total tax over the ten years | {rupees(tax_a)} | {rupees(tax_b)} |")
    A("")
    wiped = next((r["_wiped_by_s79"] for r in chain_s79
                  if r["_wiped_by_s79"] > 0), 0.0)
    if wiped:
        A(f"**{rupees(wiped)} of pre-buyback loss would be forfeited.**")
        A("")
        # The tax cost inside the window is usually nil because the company was
        # loss-making throughout - but that is NOT the same as "no cost".
        if abs(tax_b - tax_a) < 1:
            rates = load_rates()
            ay = sorted(rates["assessment_years"])[-1]
            reg = next(r for r in rates["assessment_years"][ay]["regimes"]
                       if r["id"] == "normal_25")
            future = tax_under(reg, wiped)["total"]
            A("The tax cost **within these ten years is nil** — but only because")
            A("the company had no taxable income left to shelter after the")
            A("buyback. **That is not the same as costing nothing.**")
            A("")
            A(f"The loss would have sheltered roughly **{rupees(wiped)}** of")
            A(f"future profit. At current rates that is about "
              f"**{rupees(future)}** of tax the company would pay in later")
            A("years that it otherwise would not — payable whenever it returns")
            A("to profit.")
        else:
            A(f"Additional tax within these ten years: "
              f"**{rupees(tax_b - tax_a)}**, plus the shelter lost on future")
            A("profits.")
        A("")
        A("This is why the register of members matters.")
        A("")

    # ---- assumptions ----
    A("## Four assumptions — each of which could change the answer")
    A("")
    A("| # | Assumption | Why it might be wrong | How to settle it |")
    A("|---|---|---|---|")
    A("| 1 | Losses are as computed from the books | Assessed loss can differ "
      "from book loss after disallowances | Filed returns and assessment "
      "orders |")
    A("| 2 | The whole loss is **business loss** | Part is likely "
      "**unabsorbed depreciation** (s.32(2)), which carries forward "
      "**indefinitely** and is **not** caught by s.79 | Schedule CFL of the "
      "filed ITRs |")
    A("| 3 | Returns were filed within the s.139(1) due date | A late return "
      "forfeits carry-forward of business loss entirely (s.80) | "
      "Acknowledgements for FY2020-21 and FY2021-22 |")
    A("| 4 | s.79 was not triggered | 24.99% of shares were bought back in "
      "FY2021-22; sellers are not named in the books | Register of members, "
      "Form SH-11 |")
    A("")
    A("**Assumption 2 is the most consequential.** If a large part of the")
    A("accumulated loss is unabsorbed depreciation, it never expires under the")
    A("eight-year rule and survives s.79 — which would make the position")
    A("materially better than the table above shows.")
    A("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out")
    ap.add_argument("--years", nargs="*", default=YEARS)
    args = ap.parse_args()

    print("computing chain (losses carried forward)...")
    chain = run_chain(args.years, apply_s79=False)
    print("computing s.79 scenario...")
    chain_s79 = run_chain(args.years, apply_s79=True)

    company = chain[0]["company"]
    report = render(chain, chain_s79, company)

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, "Tax-Computation-TEN-YEARS.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"written: {path}")
        for r in chain:
            print(f"  {r['fy']}: GTI {r['gross_total_income']:>16,.2f}  "
                  f"set-off {r['loss_used']:>14,.2f}  "
                  f"TI {r['total_income']:>16,.2f}  "
                  f"c/f {r['_closing_pool']:>16,.2f}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
