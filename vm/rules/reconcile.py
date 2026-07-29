#!/usr/bin/env python3
"""
Continuous reconciliation — bank against books, exceptions that persist.

The existing matcher (vm/app/lib/recon.js) is good and is not replaced: four
progressive passes plus symmetric-group pairing, and matching is pure code —
the model never decides that two things matched. What it lacks is CONTINUITY.
It runs a session at a time, so nothing accumulates and nothing is watched
across periods.

This adds the missing half:

  * every bank line is loaded and kept, keyed so re-loading never duplicates
  * exceptions are recorded and survive between runs
  * coverage is tracked per financial year, so "no statement for FY2016-17"
    is an answer rather than a silence
  * a bank line with no voucher stays open until someone resolves it

The distinction that makes this useful:

  bank line, no voucher   -> MISSING ENTRY. Money moved and the books
                             do not know. This is the finding.
  voucher, no bank line   -> accrual, provision, or an ERROR.

Real evidence for why: ~₹3,00,000 of payments to one vendor sat in the bank
and not in Tally across four years, and 11 of 12 monthly TDS challans were
unrecorded in a year that was audited and signed.

Usage
-----
    python3 reconcile.py --load-statement STATEMENT.pdf --account 239005001481
    python3 reconcile.py --status
    python3 reconcile.py --exceptions --fy 2025-26
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

DSN = os.environ.get(
    "MUNSHI_KB_DSN", "postgresql://postgres@localhost/munshi_kb"
)

try:
    import psycopg
except ImportError:
    psycopg = None


def require_db():
    if psycopg is None:
        sys.exit("psycopg not installed. Run: pip install 'psycopg[binary]'")


def fy_of(d: date) -> str:
    return f"{d.year}-{str(d.year + 1)[2:]}" if d.month >= 4 else f"{d.year - 1}-{str(d.year)[2:]}"


# ---------------------------------------------------------------------------
# Statement parsing
# ---------------------------------------------------------------------------

DATE_PATTERNS = [
    (re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})"), lambda m: date(int(m[3]), int(m[2]), int(m[1]))),
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), lambda m: date(int(m[1]), int(m[2]), int(m[3]))),
    (re.compile(r"(\d{1,2})[/-]([A-Za-z]{3})[a-z]*[/-](\d{4})"),
     lambda m: date(int(m[3]), MONTHS[m[2].lower()[:3]], int(m[1]))),
]
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


# Lines that look transactional but are not: printed timestamps, balance
# footers, page furniture. Each pattern here comes from a real false positive.
NOISE_RE = re.compile(
    r"(date\s+and\s+time|lien\s+balance|available\s+balance|closing\s+balance"
    r"|opening\s+balance|statement\s+(of|period|date)|page\s+\d+\s+of"
    r"|printed\s+on|generated\s+on|total\s*:?\s*$|grand\s+total"
    r"|\d{1,2}[.:]\d{2}\s*(am|pm)\b)",
    re.I,
)


def parse_amount(s: str) -> float | None:
    s = re.sub(r"[₹,\s]", "", str(s or ""))
    if not s or s in ("-", "."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def row_hash(account: str, d: date, desc: str, debit, credit) -> str:
    """Idempotency key. Deliberately includes the description: two identical
    amounts on one day are common (two ₹400 fees), and collapsing them would
    silently drop a real transaction."""
    blob = f"{account}|{d}|{desc.strip()[:200]}|{debit or 0}|{credit or 0}"
    return hashlib.sha256(blob.encode()).hexdigest()


def parse_statement_text(text: str) -> list[dict]:
    """Extract transactions from statement text.

    Deliberately conservative: a line is only accepted when a date AND at
    least one amount are present. Under-reading is recoverable; inventing a
    transaction is not.
    """
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) < 20:
            continue
        d = None
        for pat, conv in DATE_PATTERNS:
            m = pat.search(line)
            if m:
                try:
                    d = conv(m)
                    break
                except (ValueError, KeyError):
                    continue
        if not d:
            continue
        # Reject statement furniture that merely contains a date and a number.
        # Found in real output: a printed timestamp ("12.44 PM") and a
        # "Lien Balance: 0.00" footer were both parsed as transactions.
        # Inventing a transaction is the one failure mode that is not
        # recoverable by re-reading, so the filters are deliberately strict.
        if NOISE_RE.search(line):
            continue

        nums = re.findall(r"[\d,]+\.\d{2}", line)
        if not nums:
            continue
        amounts = [parse_amount(n) for n in nums]
        amounts = [a for a in amounts if a is not None]
        if not amounts:
            continue
        # A real transaction line moves money. All-zero amounts are footers.
        if not any(a for a in amounts if a > 0):
            continue
        out.append({"date": d, "description": line, "amounts": amounts})
    return out


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def ensure_account(conn, account_number: str, bank: str = "ICICI Bank") -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM bank_account WHERE account_number=%s", (account_number,))
        r = cur.fetchone()
        if r:
            return r[0]
        cur.execute(
            "INSERT INTO bank_account (account_number, bank_name) VALUES (%s,%s) RETURNING id",
            (account_number, bank),
        )
        return cur.fetchone()[0]


def load_transactions(conn, account_id: int, account_number: str,
                      txns: list[dict], source_doc: int | None = None) -> tuple[int, int]:
    added = skipped = 0
    with conn.cursor() as cur:
        for t in txns:
            amts = t["amounts"]
            # Heuristic: the last figure on a statement line is usually the
            # running balance; the one before it is the movement.
            balance = amts[-1] if len(amts) > 1 else None
            movement = amts[-2] if len(amts) > 1 else amts[0]
            h = row_hash(account_number, t["date"], t["description"], movement, None)
            cur.execute("SELECT 1 FROM bank_transaction WHERE row_hash=%s", (h,))
            if cur.fetchone():
                skipped += 1
                continue
            cur.execute(
                """INSERT INTO bank_transaction
                   (account_id, txn_date, description, debit, credit, balance,
                    source_document, row_hash)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (account_id, t["date"], t["description"][:1000], movement, None,
                 balance, source_doc, h),
            )
            added += 1
    conn.commit()
    return added, skipped


def update_coverage(conn, fy: str, evidence_type: str, status: str, detail: str = ""):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO coverage (fin_year, evidence_type, status, detail)
               VALUES (%s,%s,%s,%s)
               ON CONFLICT (fin_year, evidence_type)
               DO UPDATE SET status=EXCLUDED.status, detail=EXCLUDED.detail,
                             checked_on=CURRENT_DATE""",
            (fy, evidence_type, status, detail),
        )
    conn.commit()


def record_finding(conn, ref: str, fy: str, category: str, description: str,
                   amount: float | None, evidence: str, severity: str = "medium"):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO finding (ref, fin_year, category, severity,
                                    description, amount, evidence)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (ref) DO NOTHING""",
            (ref, fy, category, severity, description, amount, evidence),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def show_status(conn):
    with conn.cursor() as cur:
        print("\nBank transactions loaded")
        print("-" * 62)
        cur.execute("""
            SELECT a.account_number,
                   count(*), min(b.txn_date), max(b.txn_date)
            FROM bank_transaction b JOIN bank_account a ON a.id=b.account_id
            GROUP BY 1 ORDER BY 1
        """)
        rows = cur.fetchall()
        if not rows:
            print("  none yet")
        for acct, n, lo, hi in rows:
            print(f"  {acct}  {n:>6,} txns   {lo} → {hi}")

        print("\nEvidence coverage by year")
        print("-" * 62)
        cur.execute("""
            SELECT fin_year,
                   max(CASE WHEN evidence_type='bank-statement' THEN status END),
                   max(CASE WHEN evidence_type='tally' THEN status END),
                   max(CASE WHEN evidence_type='financials' THEN status END)
            FROM coverage GROUP BY fin_year ORDER BY fin_year
        """)
        print(f"  {'FY':10} {'bank':10} {'tally':10} {'financials':10}")
        for fy, bank, tally, fin in cur.fetchall():
            flag = "  <-- cannot verify" if bank in ("missing", None) else ""
            print(f"  {fy:10} {str(bank or '-'):10} {str(tally or '-'):10} {str(fin or '-'):10}{flag}")

        print("\nOpen findings")
        print("-" * 62)
        cur.execute("""
            SELECT ref, fin_year, severity, description, amount
            FROM finding WHERE status='open'
            ORDER BY CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                     amount DESC NULLS LAST
        """)
        rows = cur.fetchall()
        if not rows:
            print("  none recorded")
        for ref, fy, sev, desc, amt in rows:
            amt_s = f"{amt:,.0f}" if amt else ""
            print(f"  {ref}  {fy or '':8} {sev:6} {amt_s:>12}  {desc[:60]}")
        print()


def show_exceptions(conn, fy: str | None):
    """Bank lines with no matching voucher — the actual product."""
    with conn.cursor() as cur:
        q = """SELECT b.txn_date, b.description, b.debit, b.credit, a.account_number
               FROM bank_transaction b
               JOIN bank_account a ON a.id=b.account_id
               LEFT JOIN recon_match m ON m.bank_txn_id=b.id AND m.voucher_id IS NOT NULL
               WHERE m.id IS NULL"""
        params: list = []
        if fy:
            y = int(fy.split("-")[0])
            q += " AND b.txn_date BETWEEN %s AND %s"
            params += [date(y, 4, 1), date(y + 1, 3, 31)]
        q += " ORDER BY b.txn_date LIMIT 200"
        cur.execute(q, params)
        rows = cur.fetchall()

    print(f"\nBank lines with no matching voucher{f' — FY {fy}' if fy else ''}")
    print("-" * 62)
    if not rows:
        print("  none — every loaded bank line has a voucher, "
              "or no vouchers have been loaded yet")
        print()
        return
    total = 0.0
    for d, desc, debit, credit, acct in rows:
        amt = debit or credit or 0
        total += float(amt)
        print(f"  {d}  {float(amt):>12,.2f}  {desc[:60]}")
    print("-" * 62)
    print(f"  {len(rows)} line(s), {total:,.2f} total")
    print("  Each is either a missing book entry or an unrecorded transfer.")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Continuous bank reconciliation")
    ap.add_argument("--load-statement", metavar="FILE")
    ap.add_argument("--account", default="239005001481")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--exceptions", action="store_true")
    ap.add_argument("--fy")
    args = ap.parse_args()

    require_db()
    with psycopg.connect(DSN) as conn:
        if args.load_statement:
            path = Path(args.load_statement)
            if not path.exists():
                sys.exit(f"Not found: {path}")
            try:
                from pypdf import PdfReader
            except ImportError:
                sys.exit("pip install pypdf")
            text = ""
            if path.suffix.lower() == ".pdf":
                r = PdfReader(str(path))
                for p in r.pages:
                    try:
                        text += (p.extract_text() or "") + "\n"
                    except Exception:
                        pass
            else:
                text = path.read_text(errors="replace")

            txns = parse_statement_text(text)
            if not txns:
                print(f"No transactions parsed from {path.name}.")
                print("If the statement is a scan, it needs OCR — it is not empty.")
                return 1

            acct_id = ensure_account(conn, args.account)
            added, skipped = load_transactions(conn, acct_id, args.account, txns)
            years = {fy_of(t["date"]) for t in txns}
            for fy in years:
                update_coverage(conn, fy, "bank-statement", "held",
                                f"loaded from {path.name}")
            print(f"{path.name}: {added} new, {skipped} already present "
                  f"({', '.join(sorted(years))})")
            return 0

        if args.exceptions:
            show_exceptions(conn, args.fy)
            return 0

        show_status(conn)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
