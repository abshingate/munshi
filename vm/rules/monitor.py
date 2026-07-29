#!/usr/bin/env python3
"""
Compliance monitor — nothing is missed, nothing is discovered late.

Two jobs:

  1. DEADLINES  — what is due, what is overdue, what is approaching.
  2. THRESHOLDS — which vendors are near or over a TDS threshold, checked
                  cumulatively, BEFORE the next payment rather than after.

The second is the one that matters most. A real vendor was paid gross for
four consecutive years, accumulating ~₹47,000 of undeducted TDS, purely
because nobody was watching the running total. That is a monitoring failure,
not a knowledge failure — the rule was always clear.

Reads the register (CSV today, the knowledge base later) and answers through
the rules engine, so it holds no tax knowledge of its own.

Usage
-----
    python3 monitor.py                       # full status
    python3 monitor.py --check-payment "ARTH & ASSOCIATES" 125000 tds-professional-fees
    python3 monitor.py --json                # machine-readable
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tds_engine import TdsEngine  # noqa: E402

# Where the working data lives. Overridable so other companies can point it
# at their own files without editing code.
TDS_DIR = Path(os.environ.get(
    "MUNSHI_TDS_DIR",
    "/Users/admin/Documents/Exadatum/Financials/TDS",
))

WARN_DAYS = 10          # start warning this far ahead of a deadline
NEAR_THRESHOLD = 0.80   # flag a vendor at 80% of a threshold


def fy_of(d: date) -> str:
    """Indian financial year label for a date (April–March)."""
    return f"{d.year}-{str(d.year + 1)[2:]}" if d.month >= 4 else f"{d.year - 1}-{str(d.year)[2:]}"


def parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


# ---------------------------------------------------------------------------
# Deadlines
# ---------------------------------------------------------------------------

def deposit_due_for(deduction_month: date) -> date:
    """7th of the following month — except March, which is 30 April."""
    if deduction_month.month == 3:
        return date(deduction_month.year, 4, 30)
    y, m = deduction_month.year, deduction_month.month + 1
    if m > 12:
        y, m = y + 1, 1
    return date(y, m, 7)


def quarter_return_dues(today: date) -> list[dict]:
    """Return due dates for the quarters around today."""
    out = []
    for (q, end_m, end_d, due_m, due_d) in [
        ("Q1", 6, 30, 7, 31), ("Q2", 9, 30, 10, 31),
        ("Q3", 12, 31, 1, 31), ("Q4", 3, 31, 5, 31),
    ]:
        for yr in (today.year - 1, today.year):
            due_year = yr + 1 if q in ("Q3", "Q4") else yr
            due = date(due_year, due_m, due_d)
            if abs((due - today).days) <= 120:
                out.append({"item": f"{q} TDS return (Forms 138/140)", "due": due})
    return out


def check_deadlines(today: date) -> list[dict]:
    alerts: list[dict] = []

    # --- salary schedule ---------------------------------------------------
    sched = TDS_DIR / "FY2026-27" / "salary-tds-schedule.csv"
    if sched.exists():
        for row in csv.DictReader(sched.open()):
            if (row.get("status") or "").strip().lower().startswith("deposited"):
                continue
            due = parse_date(row.get("deposit_due", ""))
            if not due:
                continue
            amt = float(row.get("combined_tds_to_deposit") or 0)
            if amt <= 0:
                continue
            days = (due - today).days
            if days < 0:
                alerts.append({"severity": "overdue", "days": days, "due": due,
                               "item": f"Salary TDS {row['pay_month']}", "amount": amt,
                               "detail": f"{-days} days overdue — interest at 1.5%/month is running"})
            elif days <= WARN_DAYS:
                alerts.append({"severity": "due-soon", "days": days, "due": due,
                               "item": f"Salary TDS {row['pay_month']}", "amount": amt,
                               "detail": f"due in {days} days"})

    # --- vendor TDS awaiting deposit ---------------------------------------
    reg = TDS_DIR / "FY2026-27" / "tds-register.csv"
    if reg.exists():
        pending: dict[str, float] = defaultdict(float)
        for row in csv.DictReader(reg.open()):
            tds = float(row.get("tds_amount") or 0)
            if tds <= 0 or (row.get("challan_cin") or "").strip():
                continue
            booked = parse_date(row.get("booked_or_paid_date", ""))
            if not booked:
                continue
            pending[booked.strftime("%Y-%m")] += tds

        for month_key, amt in sorted(pending.items()):
            y, m = map(int, month_key.split("-"))
            due = deposit_due_for(date(y, m, 1))
            days = (due - today).days
            if days < 0:
                alerts.append({"severity": "overdue", "days": days, "due": due,
                               "item": f"Vendor TDS deducted {month_key}", "amount": amt,
                               "detail": f"{-days} days overdue — interest at 1.5%/month is running"})
            elif days <= WARN_DAYS:
                alerts.append({"severity": "due-soon", "days": days, "due": due,
                               "item": f"Vendor TDS deducted {month_key}", "amount": amt,
                               "detail": f"due in {days} days"})

    # --- quarterly returns --------------------------------------------------
    # Suppress a quarter that already has an acknowledgement in the register.
    # An alert that fires for work already done trains the operator to ignore
    # alerts, which is worse than not having them.
    filed_quarters = set()
    if reg.exists():
        for row in csv.DictReader(reg.open()):
            if (row.get("return_ack_no") or "").strip():
                q = (row.get("quarter") or "").strip()
                if q:
                    filed_quarters.add(q)

    for q in quarter_return_dues(today):
        quarter_label = q["item"].split()[0]          # 'Q1'
        if quarter_label in filed_quarters:
            continue
        days = (q["due"] - today).days
        if 0 <= days <= WARN_DAYS:
            alerts.append({"severity": "due-soon", "days": days, "due": q["due"],
                           "item": q["item"], "amount": None,
                           "detail": f"due in {days} days"})

    alerts.sort(key=lambda a: a["due"])
    return alerts


# ---------------------------------------------------------------------------
# Thresholds — the four-year failure this exists to prevent
# ---------------------------------------------------------------------------

SECTION_TO_RULE = {
    "194J": "tds-professional-fees",
    "194I": "tds-rent-land-building",
    "194C": "tds-contractor-company",
    "194H": "tds-commission-other",
    "194A": "tds-interest",
    "94J": "tds-professional-fees",
    "94I": "tds-rent-land-building",
    "94C": "tds-contractor-company",
}


def check_thresholds(today: date, engine: TdsEngine) -> list[dict]:
    """Running totals per vendor per section, against the applicable threshold."""
    reg = TDS_DIR / "FY2026-27" / "tds-register.csv"
    if not reg.exists():
        return []

    fy = fy_of(today)
    totals: dict[tuple[str, str], float] = defaultdict(float)
    deducted: dict[tuple[str, str], float] = defaultdict(float)

    for row in csv.DictReader(reg.open()):
        d = parse_date(row.get("booked_or_paid_date", "")) or parse_date(row.get("invoice_date", ""))
        if not d or fy_of(d) != fy:
            continue
        section = (row.get("section") or "").strip()
        vendor = (row.get("vendor_name") or "").strip()
        if not vendor or not section:
            continue
        key = (vendor, section)
        totals[key] += float(row.get("tds_base") or 0)
        deducted[key] += float(row.get("tds_amount") or 0)

    out = []
    for (vendor, section), base in sorted(totals.items(), key=lambda x: -x[1]):
        rule_id = SECTION_TO_RULE.get(section)
        if not rule_id:
            continue
        try:
            rule = engine.rule_for(rule_id)
        except (KeyError, ValueError):
            continue

        threshold = rule.get("threshold")
        basis = rule.get("threshold_basis")
        if not threshold or basis == "per_month":
            # Monthly-basis rules are judged per payment, not on a running
            # total — summing them would recreate the exact error the engine
            # was written to prevent.
            continue

        pct = base / threshold if threshold else 0
        status = None
        if pct >= 1.0 and deducted[(vendor, section)] == 0:
            status = "breached-undeducted"
            detail = (f"paid {base:,.0f} against a {threshold:,.0f} threshold with "
                      f"NO TDS deducted — catch-up is due on the whole aggregate")
        elif pct >= 1.0:
            status = "breached-ok"
            detail = f"over the threshold; {deducted[(vendor, section)]:,.0f} deducted"
        elif pct >= NEAR_THRESHOLD:
            status = "approaching"
            detail = (f"at {pct:.0%} of the {threshold:,.0f} threshold — the next "
                      f"invoice likely triggers TDS on the whole aggregate")
        if status:
            out.append({"vendor": vendor, "section": section, "rule": rule_id,
                        "paid_ytd": base, "threshold": threshold,
                        "deducted": deducted[(vendor, section)],
                        "status": status, "detail": detail})
    return out


# ---------------------------------------------------------------------------
# Pre-payment check — the intervention point
# ---------------------------------------------------------------------------

def check_payment(vendor: str, amount: float, rule_id: str,
                  today: date, engine: TdsEngine) -> dict:
    """Answer 'what happens if I pay this?' BEFORE the money moves.

    Checking after payment is how gross payments accumulate: by then the only
    remedy is a catch-up deposit plus interest.
    """
    reg = TDS_DIR / "FY2026-27" / "tds-register.csv"
    prior = 0.0
    fy = fy_of(today)
    if reg.exists():
        for row in csv.DictReader(reg.open()):
            if (row.get("vendor_name") or "").strip().lower() != vendor.strip().lower():
                continue
            d = parse_date(row.get("booked_or_paid_date", "")) or parse_date(row.get("invoice_date", ""))
            if d and fy_of(d) == fy:
                prior += float(row.get("tds_base") or 0)

    a = engine.assess(rule_id, amount, today, prior_year_total=prior)
    return {
        "vendor": vendor, "amount": amount, "prior_ytd": prior,
        "applies": a.applies, "tds": a.tds, "rate": a.rate,
        "net_payable": round(amount - a.tds, 2),
        "catch_up_on": a.catch_up_on,
        "requires_human": a.requires_human,
        "explanation": a.explanation, "authority": a.authority,
        "warnings": a.warnings,
    }


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Compliance monitor")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for testing")
    ap.add_argument("--check-payment", nargs=3, metavar=("VENDOR", "AMOUNT", "RULE_ID"),
                    help="test a payment before making it")
    args = ap.parse_args()

    today = parse_date(args.today) if args.today else date.today()
    engine = TdsEngine()

    if args.check_payment:
        vendor, amount, rule_id = args.check_payment
        res = check_payment(vendor, float(amount), rule_id, today, engine)
        if args.json:
            print(json.dumps(res, indent=2, default=str))
        else:
            print(f"\nBefore paying {vendor} {float(amount):,.2f}:\n")
            print(f"  {res['explanation']}")
            if res["applies"]:
                print(f"\n  TDS to withhold : {res['tds']:,.2f}")
                print(f"  PAY THE VENDOR  : {res['net_payable']:,.2f}")
                if res["catch_up_on"]:
                    print(f"  ! includes catch-up on {res['catch_up_on']:,.2f} "
                          f"of earlier untaxed payments")
            else:
                print(f"\n  PAY THE VENDOR  : {res['net_payable']:,.2f} (gross)")
            if res["requires_human"]:
                print("\n  ** STOP: this needs a human decision. **")
            for w in res["warnings"]:
                print(f"  ! {w}")
            print(f"\n  Authority: {res['authority']}")
        return 0

    alerts = check_deadlines(today)
    thresholds = check_thresholds(today, engine)

    if args.json:
        print(json.dumps({"as_of": str(today), "deadlines": alerts,
                          "thresholds": thresholds}, indent=2, default=str))
        return 1 if any(a["severity"] == "overdue" for a in alerts) else 0

    print(f"\nCompliance status as at {today:%d %B %Y}")
    print("=" * 62)

    overdue = [a for a in alerts if a["severity"] == "overdue"]
    soon = [a for a in alerts if a["severity"] == "due-soon"]

    if overdue:
        print("\nOVERDUE")
        for a in overdue:
            amt = f"{a['amount']:,.2f}" if a["amount"] else ""
            print(f"  {a['item']:38} {amt:>12}  {a['detail']}")
    if soon:
        print("\nDUE SOON")
        for a in soon:
            amt = f"{a['amount']:,.2f}" if a["amount"] else ""
            print(f"  {a['item']:38} {amt:>12}  {a['detail']} ({a['due']:%d %b})")
    if not overdue and not soon:
        print("\n  No deadlines within the next "
              f"{WARN_DAYS} days, and nothing overdue.")

    breached = [t for t in thresholds if t["status"] == "breached-undeducted"]
    approaching = [t for t in thresholds if t["status"] == "approaching"]

    if breached:
        print("\nTHRESHOLD BREACHED, NO TDS DEDUCTED")
        for t in breached:
            print(f"  {t['vendor'][:34]:36} {t['section']:6} {t['detail']}")
    if approaching:
        print("\nAPPROACHING A THRESHOLD")
        for t in approaching:
            print(f"  {t['vendor'][:34]:36} {t['section']:6} {t['detail']}")

    print()
    return 1 if overdue or breached else 0


if __name__ == "__main__":
    raise SystemExit(main())
