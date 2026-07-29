#!/usr/bin/env python3
"""
Evidence completeness — which transactions have no supporting document?

Documents are already searchable (kb) and filed entries already carry a
`[M-...]` marker back to their voucher (ADR-0012). Both answer "find the
document for this entry".

This answers the harder, more useful question: **what is missing?**

An audit asks "show me the invoice for this payment". The expensive answer is
"give me a week to look". The cheap answer needs a list, maintained
continuously, of every transaction lacking evidence — before anyone asks.

What counts as evidence depends on the transaction, so this does not apply a
single rule. A vendor payment needs an invoice. A tax payment needs a
challan. A bank charge needs nothing. Encoding that judgement is the point;
`EVIDENCE_RULES` below is the whole policy and is meant to be edited.

Usage
-----
    python3 evidence.py --report               # completeness by year
    python3 evidence.py --missing --fy 2025-26 # what to go and find
    python3 evidence.py --missing --min 10000  # material items only
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date

DSN = os.environ.get("MUNSHI_KB_DSN", "postgresql://postgres@localhost/munshi_kb")

try:
    import psycopg
except ImportError:
    psycopg = None


# ---------------------------------------------------------------------------
# Policy: what evidence does a transaction need?
#
# Ordered — first match wins, so specific patterns precede general ones.
# `needs` of None means no document is expected, and the transaction is
# excluded from the completeness percentage rather than counted as a failure.
# Counting bank charges as "missing evidence" would bury the real gaps.
# ---------------------------------------------------------------------------

EVIDENCE_RULES = [
    # --- no document expected --------------------------------------------
    (r"\bint on fd/rd|interest credit|int\.pd|savings interest\b", None,
     "bank-credited interest — the statement is the evidence"),
    (r"\bcharges?|fee\b.*\b(bank|sms|atm|annual)|\bgst on|service charge", None,
     "bank charge — statement is sufficient"),
    (r"\btrf to fd|fd closure|closure proceeds|trf from fd|sweep\b", None,
     "internal transfer between own accounts"),
    (r"\bacct clos tran|account closure", None,
     "account closure transfer"),
    (r"\bopening balance|closing balance|b/f|c/f\b", None,
     "balance line, not a transaction"),

    # --- statutory payments: challan required -----------------------------
    (r"\bdtax\b|/dtax/|direct tax|tds|tcs\b", "challan",
     "tax payment — challan receipt required"),
    (r"\bgst|gstn|idtx\b", "challan",
     "GST payment — challan required"),
    (r"\bepfo?\b|provident", "challan",
     "EPF payment — ECR and challan required"),
    (r"\besic\b", "challan", "ESIC payment — challan required"),
    (r"\bptrc|ptec|professional tax", "challan",
     "professional tax — challan required"),

    # --- payroll ----------------------------------------------------------
    (r"\bsalary|payroll|wages\b", "payslip",
     "salary payment — payslip or salary register required"),

    # --- everything else that moves money out ------------------------------
    (r"\brent\b", "invoice", "rent — agreement and receipt required"),
    (r".*", "invoice", "vendor payment — invoice required"),
]


def evidence_needed(description: str, is_debit: bool) -> tuple[str | None, str]:
    """What document should support this line, and why."""
    text = (description or "").lower()
    for pattern, needs, reason in EVIDENCE_RULES:
        if re.search(pattern, text):
            # Money coming IN is usually a receipt or refund; the fallback
            # "invoice required" rule is written for outgoing payments.
            if needs == "invoice" and not is_debit:
                return ("receipt", "money received — supporting document required")
            return (needs, reason)
    return (None, "unclassified")


# ---------------------------------------------------------------------------

def require_db():
    if psycopg is None:
        sys.exit("psycopg not installed. Run: pip install 'psycopg[binary]'")


def fy_bounds(fy: str) -> tuple[date, date]:
    y = int(fy.split("-")[0])
    return date(y, 4, 1), date(y + 1, 3, 31)


def find_evidence(conn, txn_date: date, amount: float, description: str) -> dict | None:
    """Look for a document that plausibly supports this transaction.

    Deliberately conservative about what counts as a match: an amount within
    a few rupees AND a date within a fortnight. A loose match that reports
    "evidence found" when it has not been is worse than reporting a gap,
    because it closes the question wrongly.
    """
    if not amount:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, filename, doc_type, doc_date, amount, source_path
               FROM kb_document
               WHERE amount IS NOT NULL
                 AND abs(amount - %s) < 1.0
                 AND doc_date BETWEEN %s - INTERVAL '15 days'
                                  AND %s + INTERVAL '15 days'
               ORDER BY abs(doc_date - %s) LIMIT 1""",
            (amount, txn_date, txn_date, txn_date),
        )
        r = cur.fetchone()
        if r:
            return {"id": r[0], "filename": r[1], "doc_type": r[2],
                    "doc_date": r[3], "amount": float(r[4] or 0), "path": r[5],
                    "match": "amount and date"}

        # Fall back to a distinctive token from the narration — a challan
        # number, invoice reference, or counterparty name.
        tokens = [t for t in re.findall(r"[A-Za-z]{5,}|\d{6,}", description or "")
                  if t.lower() not in ("account", "transfer", "payment", "banking")]
        for tok in tokens[:3]:
            cur.execute(
                """SELECT id, filename, doc_type, doc_date, amount, source_path
                   FROM kb_document
                   WHERE (filename ILIKE %s OR body_text ILIKE %s)
                     AND doc_date BETWEEN %s - INTERVAL '30 days'
                                      AND %s + INTERVAL '30 days'
                   LIMIT 1""",
                (f"%{tok}%", f"%{tok}%", txn_date, txn_date),
            )
            r = cur.fetchone()
            if r:
                return {"id": r[0], "filename": r[1], "doc_type": r[2],
                        "doc_date": r[3], "amount": float(r[4] or 0),
                        "path": r[5], "match": f"reference '{tok}'"}
    return None


def assess(conn, fy: str | None, min_amount: float = 0.0) -> dict:
    """Classify every bank transaction by evidence status."""
    q = """SELECT b.id, b.txn_date, b.description, b.debit, b.credit
           FROM bank_transaction b"""
    params: list = []
    if fy:
        lo, hi = fy_bounds(fy)
        q += " WHERE b.txn_date BETWEEN %s AND %s"
        params += [lo, hi]
    q += " ORDER BY b.txn_date"

    with conn.cursor() as cur:
        cur.execute(q, params)
        rows = cur.fetchall()

    result = {"total": 0, "not_required": 0, "found": 0, "missing": 0,
              "missing_items": [], "by_type": {}}

    for txn_id, d, desc, debit, credit in rows:
        amount = float(debit or credit or 0)
        is_debit = bool(debit)
        needs, reason = evidence_needed(desc, is_debit)
        result["total"] += 1

        if needs is None:
            result["not_required"] += 1
            continue

        result["by_type"].setdefault(needs, {"required": 0, "found": 0})
        result["by_type"][needs]["required"] += 1

        doc = find_evidence(conn, d, amount, desc)
        if doc:
            result["found"] += 1
            result["by_type"][needs]["found"] += 1
        else:
            result["missing"] += 1
            if amount >= min_amount:
                result["missing_items"].append({
                    "id": txn_id, "date": d, "amount": amount,
                    "description": (desc or "")[:70], "needs": needs,
                    "reason": reason,
                })

    return result


def report(conn, fy: str | None):
    r = assess(conn, fy)
    scope = f"FY {fy}" if fy else "all loaded periods"
    print(f"\nEvidence completeness — {scope}")
    print("=" * 64)

    if r["total"] == 0:
        print("  No bank transactions loaded for this period.")
        print("  Load statements first: reconcile.py --load-statement FILE")
        print()
        return

    required = r["found"] + r["missing"]
    pct = (100.0 * r["found"] / required) if required else 100.0

    print(f"  Transactions              {r['total']:>6,}")
    print(f"  No document expected      {r['not_required']:>6,}  "
          f"(interest, charges, internal transfers)")
    print(f"  Evidence required         {required:>6,}")
    print(f"    supported               {r['found']:>6,}")
    print(f"    MISSING                 {r['missing']:>6,}")
    if required:
        print(f"\n  Completeness: {pct:.1f}%")

    if r["by_type"]:
        print("\n  By document type:")
        for t, v in sorted(r["by_type"].items()):
            got, req = v["found"], v["required"]
            p = (100.0 * got / req) if req else 100.0
            print(f"    {t:10} {got:>4}/{req:<4}  {p:5.1f}%")

    if r["missing"]:
        print(f"\n  {r['missing']} transaction(s) have no supporting document.")
        print("  Run with --missing to list them.")
    print()


def list_missing(conn, fy: str | None, min_amount: float):
    r = assess(conn, fy, min_amount)
    items = sorted(r["missing_items"], key=lambda x: -x["amount"])
    scope = f"FY {fy}" if fy else "all loaded periods"
    print(f"\nTransactions with no supporting document — {scope}"
          + (f", ≥ {min_amount:,.0f}" if min_amount else ""))
    print("=" * 78)
    if not items:
        print("  None. Every transaction requiring evidence has a document.\n")
        return
    for it in items:
        print(f"  {it['date']}  {it['amount']:>12,.2f}  need {it['needs']:<8} "
              f"{it['description']}")
    print("-" * 78)
    print(f"  {len(items)} item(s), {sum(i['amount'] for i in items):,.2f} total")
    print("  Each needs a document collected and filed, or a note explaining "
          "why none exists.\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Evidence completeness")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--missing", action="store_true")
    ap.add_argument("--fy")
    ap.add_argument("--min", type=float, default=0.0,
                    help="only list items at or above this amount")
    args = ap.parse_args()

    require_db()
    with psycopg.connect(DSN) as conn:
        if args.missing:
            list_missing(conn, args.fy, args.min)
        else:
            report(conn, args.fy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
