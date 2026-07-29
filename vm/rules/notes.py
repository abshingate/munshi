#!/usr/bin/env python3
"""
Notes to the financial statements — Schedule III disaggregation.

Most notes are not judgement; they are prescribed tables filled from ledger
data. This generates those:

  1  Share Capital                    — authorised, issued, subscribed
  2  Reserves and Surplus             — opening, movement, closing
  3  Long-term borrowings
  4  Trade Payables                   — with MSMED ageing buckets
  5  Other Current Liabilities
  6  Short-term Provisions
  7  Property, Plant and Equipment    — gross block / depreciation / net block
  8  Non-current Investments
  9  Trade Receivables                — with ageing
 10  Cash and Bank Balances
 11  Short-term Loans and Advances
 12  Revenue from Operations
 13  Other Income
 14  Employee Benefits Expense
 15  Finance Costs
 16  Other Expenses
 17  Earnings per Share
 18  Related Party Disclosures        — AS 18
 19  Contingent Liabilities           — PLACEHOLDER, needs management input
 20  Auditor's Remuneration

WHERE JUDGEMENT IS NEEDED it says so and leaves the space blank rather than
inventing a figure. Notes 19 in particular cannot be derived from ledgers —
a contingent liability is by definition not booked.

Usage
-----
    python notes.py --fy 2025-26 --out C:\\TallyData\\Drive\\For-CA
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from financials import fetch, classify, _clean, root_group  # noqa: E402


def rupees(x, dash=True) -> str:
    if x is None or (dash and abs(x) < 0.005):
        return "-"
    neg = x < 0
    s = f"{abs(float(x)):.2f}"
    whole, dec = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        whole = f"{head},{tail}"
    return f"({whole}.{dec})" if neg else f"{whole}.{dec}"


# Ledger-name buckets for expense notes.
EMPLOYEE = ("salary", "wages", "bonus", "gratuity", "provident", "pf ",
            "esic", "staff welfare", "employee", "director remuneration")
FINANCE = ("interest on loan", "bank interest", "finance cost", "bank charge",
           "interest expense", "processing fee")
DEPREC = ("depreciation", "amortis", "amortiz")


def bucket(name: str, keys) -> bool:
    low = name.lower()
    return any(k in low for k in keys)


def build(fy: str) -> dict:
    company, ledgers, groups = fetch(fy)
    rows = []
    for led in ledgers:
        if abs(led["closing"]) < 0.005 and abs(led["opening"]) < 0.005:
            continue
        stmt, section, sub = classify(led, groups)
        rows.append({**led, "stmt": stmt, "section": section, "sub": sub,
                     "root": root_group(led["parent"], groups)})
    return {"company": company, "fy": fy, "rows": rows}


def by_root(rows, *roots):
    return [r for r in rows if r["root"] in roots]


def note_table(A, rows, sign=1, label="Particulars"):
    """Emit a two-column note table. Returns the total."""
    A(f"| {label} | ₹ |")
    A("|---|---:|")
    total = 0.0
    for r in sorted(rows, key=lambda x: -abs(x["closing"])):
        v = sign * r["closing"]
        total += v
        A(f"| {r['name'][:58]} | {rupees(v)} |")
    A(f"| **Total** | **{rupees(total)}** |")
    A("")
    return total


def render(data: dict) -> str:
    fy = data["fy"]
    y = int(fy.split("-")[0])
    rows = data["rows"]
    as_at = f"31 March {y+1}"
    out = []
    A = out.append

    A(f"# {data['company'].split(' - (')[0]}")
    A("")
    A(f"## Notes to the Financial Statements for the year ended {as_at}")
    A("")
    A("> ### ⚠️ DRAFT — generated from ledger data")
    A("> These notes disaggregate the balances in the financial statements.")
    A("> Notes requiring **management representation or professional")
    A("> judgement** are marked and left blank rather than filled with a")
    A("> guess — see Notes 19 and 21 in particular.")
    A("")
    A(f"*Generated {date.today().strftime('%d %B %Y')}. Figures in ₹.*")
    A("")

    pl = [r for r in rows if r["stmt"] == "P&L"]
    bs = [r for r in rows if r["stmt"] == "BS"]
    income = sum(r["closing"] for r in pl if r["section"] == "INCOME")
    expense = -sum(r["closing"] for r in pl if r["section"] == "EXPENSES")
    profit = income - expense

    n = 0

    # ---- 1 Share Capital ----
    n += 1
    A(f"### Note {n} — Share Capital")
    A("")
    cap = [r for r in bs if "share capital" in r["name"].lower()]
    if cap:
        note_table(A, cap)
        A("**Requires management input:** authorised capital, number and face")
        A("value of shares, shareholders holding more than 5%, and the")
        A("reconciliation of shares outstanding at the start and end of the")
        A("year (Schedule III requires all of these).")
    else:
        A("*No share capital ledger identified.*")
    A("")

    # ---- 2 Reserves and Surplus ----
    n += 1
    A(f"### Note {n} — Reserves and Surplus")
    A("")
    res = [r for r in bs if "reserve" in r["name"].lower()
           or "surplus" in r["name"].lower()
           or r["name"].lower().startswith("profit & loss")]
    if res:
        A("| Particulars | ₹ |")
        A("|---|---:|")
        op = sum(r["opening"] for r in res)
        cl = sum(r["closing"] for r in res)
        A(f"| Balance at the beginning of the year | {rupees(op)} |")
        A(f"| Profit / (Loss) for the year | {rupees(profit)} |")
        A(f"| **Balance at the end of the year** | **{rupees(cl)}** |")
        A("")
        movement = cl - op
        if abs(movement - profit) > 1:
            A(f"⚠️ **The movement in reserves ({rupees(movement)}) does not")
            A(f"equal the profit for the year ({rupees(profit)}).** Difference")
            A(f"{rupees(movement - profit)} — there may be a direct adjustment")
            A("to reserves (dividend, buyback, prior-period item) that needs")
            A("disclosing.")
            A("")
    A("")

    # ---- 3 Borrowings ----
    n += 1
    A(f"### Note {n} — Borrowings")
    A("")
    bor = by_root(rows, "Loans (Liability)", "Secured Loans", "Unsecured Loans",
                  "Bank OD A/c")
    if bor:
        note_table(A, bor)
        A("**Requires management input:** security offered, repayment terms,")
        A("rate of interest, and any default (Schedule III).")
    else:
        A("*Nil.*")
    A("")

    # ---- 4 Trade Payables ----
    n += 1
    A(f"### Note {n} — Trade Payables")
    A("")
    tp = by_root(rows, "Sundry Creditors")
    if tp:
        note_table(A, tp)
        A("**Requires management input — MSMED Act, 2006 disclosure:** amounts")
        A("due to micro and small enterprises, interest paid and payable. This")
        A("**cannot** be derived from ledgers; it needs each vendor's Udyam")
        A("registration status. Schedule III makes this disclosure mandatory")
        A("and its omission is a common audit qualification.")
        A("")
        A("**Ageing** (Schedule III, amended 2021) — outstanding for less than")
        A("1 year / 1-2 years / 2-3 years / more than 3 years, split between")
        A("MSME and others, and disputed dues. Derivable from bill-wise")
        A("details if bill-wise accounting is enabled in Tally.")
    else:
        A("*Nil.*")
    A("")

    # ---- 5 Other Current Liabilities ----
    n += 1
    A(f"### Note {n} — Other Current Liabilities")
    A("")
    ocl = by_root(rows, "Current Liabilities", "Duties & Taxes")
    ocl = [r for r in ocl if "provision" not in r["name"].lower()]
    if ocl:
        note_table(A, ocl)
    else:
        A("*Nil.*")
    A("")

    # ---- 6 Provisions ----
    n += 1
    A(f"### Note {n} — Provisions")
    A("")
    prov = [r for r in bs if "provision" in r["name"].lower()
            or r["root"] == "Provisions"]
    if prov:
        note_table(A, prov)
        A("**Requires actuarial input:** provision for gratuity and leave")
        A("encashment under **AS 15 / Ind AS 19** requires an actuarial")
        A("valuation. If the company holds a gratuity fund asset with no")
        A("corresponding liability, that is a reporting gap.")
    else:
        A("*Nil.*")
    A("")

    # ---- 7 PPE ----
    n += 1
    A(f"### Note {n} — Property, Plant and Equipment")
    A("")
    A("See the **Fixed Asset Register** (`Fixed-Asset-Register-FY{}.md`) for"
      .format(fy))
    A("the gross block, additions, disposals, depreciation and net block,")
    A("asset by asset, with the Schedule II working for every charge.")
    A("")
    fa = [r for r in bs if r["sub"] == "Non-Current Assets"
          and "accumulated" not in r["name"].lower()
          and not any(k in r["name"].lower()
                      for k in ("investment", "mutual fund", "fixed deposit",
                                "gratuity", "deposit"))]
    if fa:
        A("Summary of gross block:")
        A("")
        note_table(A, fa, sign=-1, label="Asset")
    A("")

    # ---- 8 Investments ----
    n += 1
    A(f"### Note {n} — Investments")
    A("")
    inv = [r for r in bs if r["root"] == "Investments"
           or "investment" in r["name"].lower()
           or "mutual fund" in r["name"].lower()]
    if inv:
        note_table(A, inv, sign=-1)
        A("**Requires management input:** classification as current or")
        A("non-current, quoted or unquoted, market value of quoted")
        A("investments, and basis of valuation (AS 13 — long-term at cost less")
        A("permanent diminution; current at lower of cost and fair value).")
    else:
        A("*Nil.*")
    A("")

    # ---- 9 Trade Receivables ----
    n += 1
    A(f"### Note {n} — Trade Receivables")
    A("")
    tr = by_root(rows, "Sundry Debtors")
    if tr:
        note_table(A, tr, sign=-1)
        A("**Requires management input:** ageing (Schedule III, amended 2021),")
        A("amounts considered doubtful, and provision for expected credit")
        A("loss. Whether a debt is doubtful is a judgement, not a calculation.")
    else:
        A("*Nil.*")
    A("")

    # ---- 10 Cash and Bank ----
    n += 1
    A(f"### Note {n} — Cash and Bank Balances")
    A("")
    cb = by_root(rows, "Bank Accounts", "Cash-in-hand", "Cash-in-Hand")
    fd = [r for r in bs if "fixed deposit" in r["name"].lower()]
    if cb or fd:
        note_table(A, cb + fd, sign=-1)
        A("**To verify:** bank confirmations / statements for every account,")
        A("and disclosure of deposits with more than 12 months' maturity.")
    else:
        A("*Nil.*")
    A("")

    # ---- 11 Loans and Advances ----
    n += 1
    A(f"### Note {n} — Short-term Loans and Advances")
    A("")
    la = by_root(rows, "Loans & Advances (Asset)", "Deposits (Asset)",
                 "Advance for Expenses", "Advance Salary/Loan to Employees")
    if la:
        note_table(A, la, sign=-1)
        A("**Requires review:** advances to directors or related parties need")
        A("separate disclosure and **s.185 Companies Act** compliance.")
    else:
        A("*Nil.*")
    A("")

    # ---- 12 Revenue ----
    n += 1
    A(f"### Note {n} — Revenue from Operations")
    A("")
    rev = [r for r in pl if r["sub"] == "Revenue from Operations"]
    if rev:
        note_table(A, rev)
    else:
        A("*Nil.*")
    A("")

    # ---- 13 Other Income ----
    n += 1
    A(f"### Note {n} — Other Income")
    A("")
    oi = [r for r in pl if r["sub"] == "Other Income"]
    if oi:
        note_table(A, oi)
    else:
        A("*Nil.*")
    A("")

    # ---- 14 Employee Benefits ----
    n += 1
    A(f"### Note {n} — Employee Benefits Expense")
    A("")
    emp = [r for r in pl if r["section"] == "EXPENSES"
           and bucket(r["name"], EMPLOYEE)]
    if emp:
        note_table(A, emp, sign=-1)
        A("**Requires disclosure:** managerial remuneration under s.197 and")
        A("Schedule V, and AS 15 defined-benefit disclosures if applicable.")
    else:
        A("*Nil.*")
    A("")

    # ---- 15 Finance Costs ----
    n += 1
    A(f"### Note {n} — Finance Costs")
    A("")
    fin = [r for r in pl if r["section"] == "EXPENSES"
           and bucket(r["name"], FINANCE)]
    if fin:
        note_table(A, fin, sign=-1)
    else:
        A("*Nil.*")
    A("")

    # ---- 16 Other Expenses ----
    n += 1
    A(f"### Note {n} — Other Expenses")
    A("")
    used = {id(r) for r in emp} | {id(r) for r in fin}
    oth = [r for r in pl if r["section"] == "EXPENSES"
           and id(r) not in used and not bucket(r["name"], DEPREC)]
    if oth:
        note_table(A, oth, sign=-1)
    else:
        A("*Nil.*")
    A("")

    # ---- 17 EPS ----
    n += 1
    A(f"### Note {n} — Earnings per Share (AS 20)")
    A("")
    A("| Particulars | ₹ |")
    A("|---|---:|")
    A(f"| Profit / (Loss) after tax | {rupees(profit)} |")
    A("| Weighted average number of equity shares | *management input* |")
    A("| Face value per share | *management input* |")
    A("| **Basic and diluted EPS** | *to be computed* |")
    A("")
    A("**Cannot be computed here** — the number of shares is not derivable")
    A("from ledger balances. Paid-up capital ÷ face value gives a count only")
    A("if no shares were issued or bought back during the year.")
    A("")

    # ---- 18 Related Party ----
    n += 1
    A(f"### Note {n} — Related Party Disclosures (AS 18)")
    A("")
    rp = [r for r in rows if any(k in r["name"].lower() for k in
          ("director", "shingate", "adv sal", "advance salary"))]
    if rp:
        A("Ledgers that appear related-party in nature:")
        A("")
        note_table(A, rp)
    A("**Requires management representation.** The list of related parties —")
    A("directors, key management personnel, their relatives, and entities they")
    A("control or significantly influence — must be provided by management.")
    A("It cannot be inferred from ledger names. For each, disclose the")
    A("relationship, transactions during the year, and closing balance.")
    A("")

    # ---- 19 Contingent Liabilities ----
    n += 1
    A(f"### Note {n} — Contingent Liabilities and Commitments")
    A("")
    A("**⚠️ CANNOT BE GENERATED — requires management representation.**")
    A("")
    A("A contingent liability is by definition *not booked*, so no ledger")
    A("holds it. Management must confirm:")
    A("")
    A("- Claims against the company not acknowledged as debts")
    A("- Guarantees given")
    A("- **Disputed tax demands** — income tax, GST, TDS defaults")
    A("- Capital commitments contracted but not provided for")
    A("- Any litigation pending")
    A("")
    A("*Note: outstanding TDS defaults and any CPC demands should be")
    A("considered here.*")
    A("")

    # ---- 20 Auditor's Remuneration ----
    n += 1
    A(f"### Note {n} — Auditor's Remuneration")
    A("")
    aud = [r for r in pl if "audit" in r["name"].lower()]
    if aud:
        note_table(A, aud, sign=-1)
        A("Split required between statutory audit, tax audit, other services,")
        A("and reimbursement of expenses.")
    else:
        A("*Nil.*")
    A("")

    # ---- 21 Judgement items ----
    n += 1
    A(f"### Note {n} — Matters requiring management representation")
    A("")
    A("Listed explicitly so none is assumed to be handled:")
    A("")
    A("| # | Matter | Why it cannot be generated |")
    A("|---|---|---|")
    A("| 1 | Contingent liabilities | Not booked anywhere by definition |")
    A("| 2 | MSMED status of creditors | Needs each vendor's Udyam registration |")
    A("| 3 | Doubtful debts provision | Recoverability is a judgement |")
    A("| 4 | Gratuity / leave encashment | Needs actuarial valuation |")
    A("| 5 | Going concern | Assessment of future operations |")
    A("| 6 | Impairment of assets | Needs recoverable amount (AS 28) |")
    A("| 7 | Related party list | Management representation |")
    A("| 8 | Share count for EPS | Not in ledger balances |")
    A("| 9 | Deferred tax asset | Needs probability of future taxable profit |")
    A("| 10 | Subsequent events | Events after the balance sheet date |")
    A("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fy", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    data = build(args.fy)
    if not data["rows"]:
        print(f"No ledger balances for FY{args.fy}.")
        return 1
    report = render(data)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, f"Notes-to-Accounts-FY{args.fy}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"written: {path}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
