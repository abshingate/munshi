#!/usr/bin/env python3
"""
Draft computation of total income and tax for a domestic company.

Starts from the book profit in the accounts, applies the disallowances that
can be detected from ledger data, and computes tax under every regime the
company could elect — so the choice is made on numbers rather than habit.

WHAT IT DETECTS AUTOMATICALLY
-----------------------------
  * income tax charged to P&L               s.40(a)(ii)
  * penalties and fines                     s.37(1)
  * book depreciation (added back)          s.32
  * TDS defaults flagged for s.40(a)(ia)    30% of the payment

WHAT IT CANNOT DETECT — and says so
-----------------------------------
  * s.43B items unpaid at the return due date  (needs payment dates)
  * s.36(1)(va) PF/ESI deposited late           (needs due-date-wise proof)
  * s.14A expenditure on exempt income          (needs apportionment)
  * tax depreciation on the block of assets     (needs the tax WDV, which is
    a different register from the Companies Act one)
  * s.43B(h) MSME payment delays                (needs vendor MSME status)

Any of these can change the answer materially. The output lists them as open
items rather than assuming they are nil.

Usage
-----
    python tax_computation.py --fy 2025-26 --out C:\\TallyData\\Drive\\For-CA
    python tax_computation.py --fy 2025-26 --brought-forward-loss 45000000
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from financials import fetch, classify  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RATES = os.path.join(HERE, "tax_rates.json")


def rupees(x) -> str:
    if x is None:
        return "-"
    neg = x < 0
    s = f"{abs(float(x)):.2f}"
    whole, dec = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        whole = f"{head},{tail}"
    return f"({whole}.{dec})" if neg else f"{whole}.{dec}"


def load_rates() -> dict:
    with open(RATES, encoding="utf-8") as fh:
        return json.load(fh)


def surcharge_rate(income: float, slabs: list) -> float:
    for s in slabs:
        lo = s["income_above"]
        hi = s["income_upto"]
        if income > lo and (hi is None or income <= hi):
            return s["rate"]
    return 0.0


def tax_under(regime: dict, total_income: float) -> dict:
    """Tax, surcharge and cess under one regime. Never negative."""
    ti = max(0.0, total_income)
    base = ti * regime["base_rate"] / 100.0
    if "surcharge_flat" in regime:
        sur_rate = regime["surcharge_flat"]
    else:
        sur_rate = surcharge_rate(ti, regime.get("surcharge_slabs", []))
    sur = base * sur_rate / 100.0
    cess = (base + sur) * regime["cess"] / 100.0
    return {"base": base, "surcharge_rate": sur_rate, "surcharge": sur,
            "cess": cess, "total": base + sur + cess}


# Detection buckets
INCOME_TAX = ("income tax", "income-tax")
PENALTY = ("penalty", "penalties", "fine", "late filing fee", "late fee")
DEPREC = ("depreciation", "amortis", "amortiz")
INTEREST_STATUTORY = ("interest on tds", "interest on pf", "interest on gst",
                      "interest on income tax", "interest on tax")


def hit(name: str, keys) -> bool:
    low = name.lower()
    return any(k in low for k in keys)


def compute(fy: str, bf_loss: float = 0.0, bf_deprec: float = 0.0,
            turnover_over_400cr: bool = False) -> dict:
    company, ledgers, groups = fetch(fy)
    rows = []
    for led in ledgers:
        if abs(led["closing"]) < 0.005:
            continue
        stmt, section, sub = classify(led, groups)
        rows.append({**led, "stmt": stmt, "section": section, "sub": sub})

    pl = [r for r in rows if r["stmt"] == "P&L"]
    income = sum(r["closing"] for r in pl if r["section"] == "INCOME")
    expense = -sum(r["closing"] for r in pl if r["section"] == "EXPENSES")
    book_profit = income - expense

    adds = []      # disallowances / add-backs
    deducts = []   # allowances

    for r in pl:
        if r["section"] != "EXPENSES":
            continue
        amt = -r["closing"]
        if amt <= 0.005:
            continue
        nm = r["name"]
        if hit(nm, INCOME_TAX):
            adds.append({"section": "40(a)(ii)", "ledger": nm, "amount": amt,
                         "why": "Income tax is not a deductible expense"})
        elif hit(nm, PENALTY):
            adds.append({"section": "37(1)", "ledger": nm, "amount": amt,
                         "why": "Penalty/fine for breach of law is not "
                                "deductible (compensatory interest may be — "
                                "confirm the nature)"})
        elif hit(nm, DEPREC):
            adds.append({"section": "32", "ledger": nm, "amount": amt,
                         "why": "Book depreciation added back; tax "
                                "depreciation on the block of assets is "
                                "deducted separately"})

    total_adds = sum(a["amount"] for a in adds)
    profit_after_adds = book_profit + total_adds

    # Set off brought-forward losses (business loss first, then unabsorbed
    # depreciation, which has no time limit).
    gross_total_income = profit_after_adds
    loss_used = min(max(0.0, gross_total_income), bf_loss)
    after_loss = gross_total_income - loss_used
    deprec_used = min(max(0.0, after_loss), bf_deprec)
    total_income = after_loss - deprec_used

    rates = load_rates()
    ay = f"{int(fy.split('-')[0])+1}-{str(int(fy.split('-')[0])+2)[2:]}"
    ay_data = rates["assessment_years"].get(ay)
    if not ay_data:
        # Fall back to the latest year we hold, and say so.
        ay = sorted(rates["assessment_years"])[-1]
        ay_data = rates["assessment_years"][ay]

    regimes = {}
    for reg in ay_data["regimes"]:
        if reg["id"] == "new_manufacturing_115BAB":
            continue  # services company
        if reg["id"] == "normal_25" and turnover_over_400cr:
            continue
        if reg["id"] == "normal_30" and not turnover_over_400cr:
            continue
        # Under 115BAA, brought-forward losses attributable to the forgone
        # deductions are lost. Model that explicitly rather than silently.
        if not reg.get("losses_allowed", True):
            ti = max(0.0, profit_after_adds)
        else:
            ti = max(0.0, total_income)
        regimes[reg["id"]] = {
            "regime": reg,
            "total_income": ti,
            "tax": tax_under(reg, ti),
        }

    # MAT — only where the regime allows it.
    mat_cfg = ay_data["mat"]
    mat_base = max(0.0, book_profit)
    mat_tax = mat_base * mat_cfg["rate_on_book_profit"] / 100.0
    mat_sur = mat_tax * surcharge_rate(mat_base, mat_cfg["surcharge_slabs"]) / 100.0
    mat_cess = (mat_tax + mat_sur) * mat_cfg["cess"] / 100.0
    mat_total = mat_tax + mat_sur + mat_cess

    return {
        "company": company, "fy": fy, "ay": ay,
        "income": income, "expense": expense, "book_profit": book_profit,
        "adds": adds, "total_adds": total_adds,
        "deducts": deducts,
        "gross_total_income": gross_total_income,
        "bf_loss": bf_loss, "loss_used": loss_used,
        "bf_deprec": bf_deprec, "deprec_used": deprec_used,
        "total_income": total_income,
        "regimes": regimes,
        "mat": {"book_profit": mat_base, "tax": mat_tax, "surcharge": mat_sur,
                "cess": mat_cess, "total": mat_total, "cfg": mat_cfg},
        "rates_verified_on": rates.get("_verified_on"),
    }


def render(res: dict) -> str:
    out = []
    A = out.append
    fy, ay = res["fy"], res["ay"]

    A(f"# {res['company'].split(' - (')[0]}")
    A("")
    A(f"## Draft Computation of Total Income — FY {fy} (AY {ay})")
    A("")
    A("> ### ⚠️ DRAFT — for review by the tax auditor")
    A("> Computed from ledger data. Several adjustments **cannot** be derived")
    A("> from ledgers and are listed as open items at the end — any one of")
    A("> them can change the liability materially. This is a starting point")
    A("> for the s.44AB tax audit, not a substitute for it.")
    A("")
    A(f"*Generated {date.today().strftime('%d %B %Y')}. "
      f"Rate card verified {res['rates_verified_on']}.*")
    A("")

    # ---- computation ----
    A("## Computation")
    A("")
    A("| Particulars | ₹ |")
    A("|---|---:|")
    A(f"| Revenue | {rupees(res['income'])} |")
    A(f"| Less: Expenses | {rupees(res['expense'])} |")
    A(f"| **Profit / (Loss) as per Statement of Profit and Loss** "
      f"| **{rupees(res['book_profit'])}** |")
    A("| | |")
    if res["adds"]:
        A("| **Add: amounts disallowed / added back** | |")
        for a in res["adds"]:
            A(f"| &nbsp;&nbsp;{a['ledger'][:40]} — s.{a['section']} "
              f"| {rupees(a['amount'])} |")
        A(f"| **Total additions** | **{rupees(res['total_adds'])}** |")
        A("| | |")
    A(f"| **Gross Total Income before set-off** "
      f"| **{rupees(res['gross_total_income'])}** |")
    if res["bf_loss"] or res["bf_deprec"]:
        A(f"| Less: brought-forward business loss set off (s.72) "
          f"| {rupees(res['loss_used'])} |")
        A(f"| Less: unabsorbed depreciation set off (s.32(2)) "
          f"| {rupees(res['deprec_used'])} |")
    A(f"| **TOTAL INCOME** | **{rupees(res['total_income'])}** |")
    A("")

    if res["book_profit"] < 0:
        A(f"**The company has a book loss of {rupees(-res['book_profit'])}.** "
          f"Subject to the adjustments below, there is no taxable income and")
        A("the loss may be carried forward — **but only if the return is filed")
        A("within the s.139(1) due date** (31 October for an audit case). A")
        A("late return forfeits the carry-forward of business loss entirely.")
        A("")

    # ---- regimes ----
    A("## Tax under each regime")
    A("")
    A("| | Total income ₹ | Tax ₹ | Surcharge ₹ | Cess ₹ | **Total ₹** |")
    A("|---|---:|---:|---:|---:|---:|")
    for rid, r in res["regimes"].items():
        t = r["tax"]
        A(f"| {r['regime']['name']} | {rupees(r['total_income'])} "
          f"| {rupees(t['base'])} | {rupees(t['surcharge'])} "
          f"| {rupees(t['cess'])} | **{rupees(t['total'])}** |")
    m = res["mat"]
    A(f"| MAT u/s 115JB @ {m['cfg']['rate_on_book_profit']}% of book profit "
      f"| {rupees(m['book_profit'])} | {rupees(m['tax'])} "
      f"| {rupees(m['surcharge'])} | {rupees(m['cess'])} "
      f"| **{rupees(m['total'])}** |")
    A("")

    # ---- recommendation ----
    normal = next((r for rid, r in res["regimes"].items()
                   if rid.startswith("normal")), None)
    baa = res["regimes"].get("concessional_115BAA")
    if normal and baa:
        normal_liab = max(normal["tax"]["total"], m["total"])
        baa_liab = baa["tax"]["total"]  # MAT does not apply under 115BAA
        A("### Which regime")
        A("")
        A(f"- **Normal regime**: tax {rupees(normal['tax']['total'])}, "
          f"MAT {rupees(m['total'])} → liability is the higher: "
          f"**{rupees(normal_liab)}**")
        A(f"- **s.115BAA**: {rupees(baa_liab)} (MAT does not apply)")
        A("")
        if baa_liab < normal_liab:
            A(f"On these figures **s.115BAA is lower by "
              f"{rupees(normal_liab - baa_liab)}**.")
        elif baa_liab > normal_liab:
            A(f"On these figures **the normal regime is lower by "
              f"{rupees(baa_liab - normal_liab)}**.")
        else:
            A("The two are equal on these figures.")
        A("")
        if res["bf_loss"] or res["bf_deprec"]:
            A("> ⚠️ **Do not elect s.115BAA on this comparison alone.** The")
            A("> option is **irrevocable**, and electing it forfeits most")
            A("> carried-forward losses and unabsorbed depreciation, plus any")
            A("> MAT credit. With losses of "
              f"{rupees(res['bf_loss'] + res['bf_deprec'])} available, giving")
            A("> them up may cost far more in later years than this year's")
            A("> saving. Model several years before filing Form 10-IC.")
            A("")

    # ---- open items ----
    A("## Open items — these can change the answer")
    A("")
    A("Not derivable from ledger balances. Each needs a decision:")
    A("")
    A("| # | Item | Section | What is needed |")
    A("|---|---|---|---|")
    A("| 1 | TDS not deducted or not deposited by the return due date | "
      "40(a)(ia) | 30% of the payment is disallowed. Cross-check the TDS "
      "register against expense ledgers. |")
    A("| 2 | Tax depreciation | 32 | Book depreciation is added back above. "
      "Tax depreciation on the **block of assets** must be computed and "
      "deducted — it is a different register from the Companies Act one. |")
    A("| 3 | Statutory dues unpaid at the return due date | 43B | GST, PF "
      "(employer), bonus, leave encashment — allowed only on actual payment. |")
    A("| 4 | Employee PF/ESI deposited after the due date under the relevant "
      "Act | 36(1)(va) | Permanently disallowed (*Checkmate Services*, SC "
      "2022). Needs deposit dates. |")
    A("| 5 | Payments to micro/small enterprises beyond the MSMED limit | "
      "43B(h) | Needs each vendor's MSME status. |")
    A("| 6 | Expenditure relating to exempt income | 14A / Rule 8D | Relevant "
      "if there is dividend or other exempt income. |")
    A("| 7 | Change in shareholding | **79** | A closely-held company loses "
      "carried-forward losses if beneficial shareholding carrying 51% of "
      "voting power changes. **Check this against any buyback or share "
      "transfer.** |")
    A("| 8 | Capital gains | 45-55 | Gains on sale of investments/property "
      "are taxed under their own heads, not as business income. |")
    A("")

    A("---")
    A("")
    A("## Basis")
    A("")
    A(f"- Rates are for **AY {ay}** from `tax_rates.json`, verified "
      f"{res['rates_verified_on']}. **Re-verify before filing** — corporate")
    A("  rates change with each Finance Act.")
    A("- Brought-forward losses were supplied as input, not derived. They must")
    A("  agree with the last accepted return / assessment order.")
    A("- MAT book profit is taken as accounting profit. Under Explanation 1 to")
    A("  s.115JB it requires its own adjustments — **this is an approximation**.")
    A("- No capital-gains computation is included.")
    A("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fy", required=True)
    ap.add_argument("--brought-forward-loss", type=float, default=0.0,
                    help="business loss carried forward from earlier years")
    ap.add_argument("--brought-forward-depreciation", type=float, default=0.0,
                    help="unabsorbed depreciation carried forward")
    ap.add_argument("--turnover-over-400cr", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()

    res = compute(args.fy, args.brought_forward_loss,
                  args.brought_forward_depreciation,
                  args.turnover_over_400cr)
    report = render(res)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, f"Tax-Computation-FY{args.fy}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"written: {path}")
        print(f"  book profit:  {res['book_profit']:,.2f}")
        print(f"  add-backs:    {res['total_adds']:,.2f}")
        print(f"  total income: {res['total_income']:,.2f}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
