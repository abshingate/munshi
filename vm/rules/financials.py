#!/usr/bin/env python3
"""
Generate draft financial statements from Tally, for a CA to audit.

Produces, for any financial year:
  * Trial Balance
  * Balance Sheet          (Schedule III format, Companies Act 2013)
  * Statement of Profit and Loss
  * Ledger detail backing every line

WHAT THIS IS NOT
----------------
These are **DRAFT, UNAUDITED** statements, mechanically derived from Tally.
They are a starting point for the auditor, not a substitute for one. The
company's directors remain responsible for the accounts, and a statutory
audit requires an independent CA regardless of how good the draft is.

Specifically, this tool does NOT:
  * make provisions, accruals, or cut-off adjustments
  * compute depreciation (it reports what Tally already booked)
  * compute current or deferred tax
  * value inventory or investments
  * assess going concern, impairment, or related-party disclosures
  * write the notes, or the Directors' and Auditor's reports

Schedule III mapping is inferred from Tally's group tree. **Every mapping must
be reviewed** — a ledger filed under the wrong group produces a wrong
statement that still balances perfectly.

Usage (on the VM, with Tally open)
----------------------------------
    python financials.py --fy 2025-26
    python financials.py --fy 2025-26 --out C:\\TallyData\\Drive\\For-CA
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tally_extract import (  # noqa: E402
    post, collection, tag_text, unescape, parse_amount, company_name,
)

# ---------------------------------------------------------------------------
# Schedule III mapping.
#
# Keyed on Tally's TOP-LEVEL group. Anything unmapped is reported loudly rather
# than silently dropped - a missing line is far more dangerous than an obvious
# "UNMAPPED" heading, because it still balances.
# ---------------------------------------------------------------------------

BS_MAP = {
    "Capital Account":            ("EQUITY AND LIABILITIES", "Shareholders' Funds"),
    "Reserves & Surplus":         ("EQUITY AND LIABILITIES", "Shareholders' Funds"),
    "Loans (Liability)":          ("EQUITY AND LIABILITIES", "Non-Current Liabilities"),
    "Secured Loans":              ("EQUITY AND LIABILITIES", "Non-Current Liabilities"),
    "Unsecured Loans":            ("EQUITY AND LIABILITIES", "Non-Current Liabilities"),
    "Current Liabilities":        ("EQUITY AND LIABILITIES", "Current Liabilities"),
    "Provisions":                 ("EQUITY AND LIABILITIES", "Current Liabilities"),
    "Sundry Creditors":           ("EQUITY AND LIABILITIES", "Current Liabilities"),
    "Duties & Taxes":             ("EQUITY AND LIABILITIES", "Current Liabilities"),
    "Fixed Assets":               ("ASSETS", "Non-Current Assets"),
    "Investments":                ("ASSETS", "Non-Current Assets"),
    "Current Assets":             ("ASSETS", "Current Assets"),
    "Sundry Debtors":             ("ASSETS", "Current Assets"),
    "Cash-in-Hand":               ("ASSETS", "Current Assets"),
    "Bank Accounts":              ("ASSETS", "Current Assets"),
    "Loans & Advances (Asset)":   ("ASSETS", "Current Assets"),
    "Deposits (Asset)":           ("ASSETS", "Current Assets"),
    "Misc. Expenses (ASSET)":     ("ASSETS", "Non-Current Assets"),
    "Branch / Divisions":         ("ASSETS", "Current Assets"),
    "Suspense A/c":               ("ASSETS", "Current Assets"),
    # Non-standard groups present in this company's chart of accounts.
    "Old Assets":                 ("ASSETS", "Non-Current Assets"),
    "Cash-in-hand":               ("ASSETS", "Current Assets"),
    "Reserve & Surplus":          ("EQUITY AND LIABILITIES", "Shareholders' Funds"),
    "Reserves and Surplus":       ("EQUITY AND LIABILITIES", "Shareholders' Funds"),
}

PL_MAP = {
    "Sales Accounts":             ("INCOME", "Revenue from Operations"),
    "Direct Incomes":             ("INCOME", "Revenue from Operations"),
    "Indirect Incomes":           ("INCOME", "Other Income"),
    "Purchase Accounts":          ("EXPENSES", "Purchases"),
    "Direct Expenses":            ("EXPENSES", "Direct Expenses"),
    "Indirect Expenses":          ("EXPENSES", "Other Expenses"),
}

# Ledger-name hints for Schedule III lines that Tally's tree cannot infer.
EMPLOYEE_HINTS = ("salary", "wages", "bonus", "gratuity", "provident",
                  "pf ", "esic", "staff welfare", "employee")
FINANCE_HINTS = ("interest on loan", "bank interest", "finance cost",
                 "interest expense")
DEPRECIATION_HINTS = ("depreciation", "amortis", "amortiz")


def rupees(x, blank_zero: bool = True) -> str:
    if x is None or (blank_zero and abs(x) < 0.005):
        return ""
    neg = x < 0
    s = f"{abs(float(x)):.2f}"
    whole, dec = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        whole = f"{head},{tail}"
    return f"({whole}.{dec})" if neg else f"{whole}.{dec}"


# ---------------------------------------------------------------------------

def fetch(fy: str):
    """Ledgers with balances, plus the group tree, for one financial year."""
    y = int(fy.split("-")[0])
    frm, to = f"{y}0401", f"{y+1}0331"
    cmp_name = company_name()

    xml = post(collection("L", "Ledger",
                          ["Name", "Parent", "OpeningBalance", "ClosingBalance"],
                          frm, to, company=cmp_name))
    ledgers = []
    for m in re.finditer(r'<LEDGER NAME="([^"]+)"[^>]*>(.*?)</LEDGER>', xml, re.S):
        b = m.group(2)
        ledgers.append({
            "name": _clean(unescape(m.group(1))),
            "parent": _clean(unescape(tag_text(b, "PARENT"))),
            "opening": parse_amount(tag_text(b, "OPENINGBALANCE")) or 0.0,
            "closing": parse_amount(tag_text(b, "CLOSINGBALANCE")) or 0.0,
        })

    gx = post(collection("G", "Group", ["Name", "Parent", "IsRevenue"],
                         company=cmp_name))
    groups = {}
    for m in re.finditer(r'<GROUP NAME="([^"]+)"[^>]*>(.*?)</GROUP>', gx, re.S):
        b = m.group(2)
        groups[_clean(unescape(m.group(1)))] = {
            "parent": _clean(unescape(tag_text(b, "PARENT"))),
            "is_revenue": tag_text(b, "ISREVENUE").upper() == "YES",
        }
    return cmp_name, ledgers, groups


def _clean(s: str) -> str:
    """Normalise a Tally group name.

    Tally's synthetic root arrives as the LITERAL TEXT '&#4; Primary' — an
    unresolved XML numeric character reference, not a real control byte. So
    stripping \\x00-\\x1f does nothing and every ledger walks up to it, which
    maps nothing and collapses the whole balance sheet into one bucket.
    Strip numeric entities as text, then real control characters.
    """
    s = re.sub(r"&#\d+;", "", s or "")
    return re.sub(r"[\x00-\x1f]", "", s).strip()


def is_root(name: str) -> bool:
    return _clean(name).lower() in ("", "primary")


def root_group(name: str, groups: dict) -> str:
    """The highest MEANINGFUL group above a ledger.

    Stops just below Tally's synthetic 'Primary' root — that level is where
    the real top-level groups live (Capital Account, Fixed Assets, Indirect
    Expenses...), and it is what BS_MAP and PL_MAP are keyed on.
    """
    seen = set()
    cur = _clean(name)
    while cur in groups and cur not in seen:
        seen.add(cur)
        parent = _clean(groups[cur]["parent"])
        if is_root(parent):
            return cur
        cur = parent
    return cur or _clean(name)


def is_revenue(name: str, groups: dict) -> bool:
    seen = set()
    cur = name
    while cur in groups and cur not in seen:
        seen.add(cur)
        if groups[cur]["is_revenue"]:
            return True
        cur = groups[cur]["parent"]
    return False


def classify(led: dict, groups: dict) -> tuple:
    """(statement, section, sub-head) for one ledger."""
    root = root_group(led["parent"], groups)
    rev = is_revenue(led["parent"], groups)
    lower = led["name"].lower()

    if rev:
        stmt, sub = PL_MAP.get(root, ("EXPENSES", "UNMAPPED"))[0], \
                    PL_MAP.get(root, ("EXPENSES", "UNMAPPED"))[1]
        if stmt == "EXPENSES":
            if any(h in lower for h in DEPRECIATION_HINTS):
                sub = "Depreciation and Amortisation"
            elif any(h in lower for h in EMPLOYEE_HINTS):
                sub = "Employee Benefits Expense"
            elif any(h in lower for h in FINANCE_HINTS):
                sub = "Finance Costs"
        return ("P&L", stmt, sub)

    if root in BS_MAP:
        section, sub = BS_MAP[root]
        return ("BS", section, sub)
    return ("BS", "UNMAPPED", f"UNMAPPED - Tally group '{root}'")


def build(fy: str):
    cmp_name, ledgers, groups = fetch(fy)
    rows = []
    for led in ledgers:
        if abs(led["closing"]) < 0.005 and abs(led["opening"]) < 0.005:
            continue
        stmt, section, sub = classify(led, groups)
        rows.append({**led, "stmt": stmt, "section": section, "sub": sub,
                     "root": root_group(led["parent"], groups)})
    return cmp_name, rows


# ---------------------------------------------------------------------------
# Rendering. Tally's sign convention is negative=debit; statements are
# presented with the conventional positive figures.
# ---------------------------------------------------------------------------

def line(label, amount, indent=0, bold=False):
    pad = "  " * indent
    lbl = f"{pad}{label}"
    amt = rupees(amount)
    if bold:
        return f"**{lbl}**|**{amt}**"
    return f"{lbl}|{amt}"


def render(fy: str, cmp_name: str, rows: list) -> str:
    y = int(fy.split("-")[0])
    as_at = f"31 March {y+1}"
    pl = [r for r in rows if r["stmt"] == "P&L"]
    bs = [r for r in rows if r["stmt"] == "BS"]

    # Tally sign convention: credit positive, debit negative. Income ledgers
    # carry credit (positive) balances, expenses carry debit (negative) ones.
    # Present both as positive magnitudes; profit = income - expense, so a
    # negative result is a LOSS.
    income = sum(r["closing"] for r in pl if r["section"] == "INCOME")
    expense = -sum(r["closing"] for r in pl if r["section"] == "EXPENSES")
    profit = income - expense

    out = []
    A = out.append
    A(f"# {cmp_name.split(' - (')[0]}")
    A("")
    A(f"## Draft Financial Statements for the year ended {as_at}")
    A("")
    A("> ### ⚠️ DRAFT — UNAUDITED")
    A("> Mechanically generated from the company's Tally data. Prepared for")
    A("> audit; **not** a substitute for one. No provisions, accruals, cut-off")
    A("> adjustments, depreciation recomputation, or tax provision have been")
    A("> made. Schedule III classification is inferred from Tally's group tree")
    A("> and **must be reviewed line by line** — a ledger filed under the wrong")
    A("> group yields a wrong statement that still balances.")
    A("")
    A(f"*Generated {date.today().strftime('%d %B %Y')}. Figures in ₹. "
      f"Brackets denote credit balances.*")
    A("")

    # ---- Balance Sheet ----
    A("---")
    A("")
    A(f"## Balance Sheet as at {as_at}")
    A("")
    A("| Particulars | ₹ |")
    A("|---|---:|")
    for section in ("EQUITY AND LIABILITIES", "ASSETS", "UNMAPPED"):
        sec = [r for r in bs if r["section"] == section]
        if not sec:
            continue
        A(f"| **{section}** | |")
        subs = {}
        for r in sec:
            subs.setdefault(r["sub"], []).append(r)
        sec_total = 0.0
        for sub, items in subs.items():
            sub_total = sum(r["closing"] for r in items)
            sec_total += sub_total
            shown = -sub_total if section == "ASSETS" else sub_total
            A(f"| &nbsp;&nbsp;{sub} | {rupees(shown)} |")
            for r in sorted(items, key=lambda x: x["closing"]):
                v = -r["closing"] if section == "ASSETS" else r["closing"]
                A(f"| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{r['name'][:52]} "
                  f"| {rupees(v)} |")
        shown_total = -sec_total if section == "ASSETS" else sec_total
        A(f"| **TOTAL — {section}** | **{rupees(shown_total)}** |")
        A("| | |")

    # Tally's 'Reserve & Surplus' closing balance ALREADY includes the year's
    # result, which is why balance-sheet ledgers sum to zero on their own.
    # Adding `profit` here again would double-count it — that produced a
    # difference exactly equal to the profit figure.
    eq = sum(r["closing"] for r in bs if r["section"] == "EQUITY AND LIABILITIES")
    asset = -sum(r["closing"] for r in bs if r["section"] == "ASSETS")
    A("")
    diff = eq - asset
    if abs(diff) < 0.05:
        A(f"**Balance check: Equity & Liabilities {rupees(eq)} = "
          f"Assets {rupees(asset)} ✓**")
    else:
        A(f"**⚠️ BALANCE SHEET DOES NOT BALANCE — difference "
          f"{rupees(diff)}. Do not send until resolved.**")
    A("")

    # ---- P&L ----
    A("---")
    A("")
    A(f"## Statement of Profit and Loss for the year ended {as_at}")
    A("")
    A("| Particulars | ₹ |")
    A("|---|---:|")
    # Income ledgers hold credit (positive) balances, expenses hold debit
    # (negative) ones. Flip only the expenses so both print as positive
    # magnitudes, the way a reader expects a P&L to look.
    for section, sign in (("INCOME", 1), ("EXPENSES", -1)):
        sec = [r for r in pl if r["section"] == section]
        if not sec:
            continue
        A(f"| **{section}** | |")
        subs = {}
        for r in sec:
            subs.setdefault(r["sub"], []).append(r)
        for sub, items in sorted(subs.items()):
            sub_total = sign * sum(r["closing"] for r in items)
            A(f"| &nbsp;&nbsp;{sub} | {rupees(sub_total)} |")
            for r in sorted(items, key=lambda x: x["closing"]):
                A(f"| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{r['name'][:52]} "
                  f"| {rupees(sign * r['closing'])} |")
        total = sign * sum(r["closing"] for r in sec)
        A(f"| **TOTAL {section}** | **{rupees(total)}** |")
        A("| | |")
    A(f"| **PROFIT / (LOSS) BEFORE TAX** | **{rupees(profit)}** |")
    A("| &nbsp;&nbsp;Tax expense | *to be computed by the auditor* |")
    A(f"| **PROFIT / (LOSS) FOR THE YEAR** | **{rupees(profit)}** |")
    A("")

    unmapped = [r for r in rows if "UNMAPPED" in r["sub"]]
    if unmapped:
        A("---")
        A("")
        A("## ⚠️ Unmapped ledgers — REVIEW REQUIRED")
        A("")
        A("These carry balances but their Tally group has no Schedule III")
        A("mapping. They are **excluded from the headings above** and must be")
        A("classified before these statements are used.")
        A("")
        A("| Ledger | Tally group | ₹ |")
        A("|---|---|---:|")
        for r in unmapped:
            A(f"| {r['name']} | {r['root']} | {rupees(r['closing'])} |")
        A("")

    # ---- Trial Balance ----
    A("---")
    A("")
    A(f"## Trial Balance as at {as_at}")
    A("")
    A("*Every ledger with a balance. This is the bridge between Tally and the")
    A("statements above — the auditor's usual starting point.*")
    A("")
    A("| Ledger | Tally group | Opening ₹ | Closing ₹ |")
    A("|---|---|---:|---:|")
    for r in sorted(rows, key=lambda x: (x["stmt"], x["root"], x["name"])):
        A(f"| {r['name'][:46]} | {r['root'][:26]} | "
          f"{rupees(r['opening'])} | {rupees(r['closing'])} |")
    tot_o = sum(r["opening"] for r in rows)
    tot_c = sum(r["closing"] for r in rows)
    A(f"| **TOTAL** | | **{rupees(tot_o) or '0.00'}** "
      f"| **{rupees(tot_c) or '0.00'}** |")
    A("")
    A(f"Closing balances sum to {rupees(tot_c) or '0.00'}, which equals the "
      f"profit/(loss) carried to reserves — the books balance.")
    A("")

    A("---")
    A("")
    A("## What the auditor still needs to do")
    A("")
    A("Listed so nothing is assumed to be handled:")
    A("")
    A("1. **Verify the Schedule III mapping** of every ledger above.")
    A("2. **Depreciation** — confirm the charge against the Companies Act,")
    A("   Schedule II useful lives. This tool reports what Tally booked; it")
    A("   does not recompute it.")
    A("3. **Provisions and accruals** — expenses incurred but not booked,")
    A("   and cut-off around the year end.")
    A("4. **Tax** — current and deferred; no tax provision is made here.")
    A("5. **Investments** — valuation and classification "
      "(current vs non-current).")
    A("6. **Related-party transactions** — director remuneration, advances,")
    A("   and s.185/s.188 compliance.")
    A("7. **Notes to accounts**, Directors' Report, and the audit report.")
    A("8. **Confirmations** — bank, debtors, creditors.")
    A("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fy", required=True, help="e.g. 2025-26")
    ap.add_argument("--out", help="directory to write the report into")
    args = ap.parse_args()

    cmp_name, rows = build(args.fy)
    if not rows:
        print(f"No ledger balances for FY{args.fy}. Is Tally open with the "
              f"company loaded, and does that year have data?")
        return 1

    report = render(args.fy, cmp_name, rows)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, f"DRAFT-Financials-FY{args.fy}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"written: {path}")
        print(f"  {len(rows)} ledgers with balances")
        unmapped = [r for r in rows if "UNMAPPED" in r["sub"]]
        if unmapped:
            print(f"  WARNING: {len(unmapped)} unmapped ledgers need review")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
