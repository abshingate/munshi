#!/usr/bin/env python3
"""
Coordinate-aware statement extraction.

Line-based parsing fails on most bank PDFs because the text layer is not
lines. A single transaction is emitted as fragments scattered over many
visual rows, wrapped mid-word, with the amount split from its own decimals:

    '25 16/Apr/2025 16/04/2025'
    '03:06:03 PMUPI/510601845599/'
    'OfficeChairs/surendr'
    'aparmar1//ICI73fd46'
    'f8eea083e/1,000.00 3,38,067.'
    '84'                              <- the balance's last two digits

Reading that as lines produces either nothing or nonsense. But the PDF knows
where every fragment sits, so this reassembles by geometry instead:

  1. collect every text fragment with its (x, y) position
  2. group fragments into visual rows by y
  3. find ANCHOR rows — those carrying a date and at least one amount
  4. attach nearby description fragments to the anchor above them
  5. read amount and balance from their x-columns, not their order

Design stance, unchanged from reconcile.py: failing to read a transaction is
recoverable by re-reading; INVENTING one is not. Every anchor must carry a
real date and a real amount, or it is discarded.

STATUS: ASSISTIVE, NOT AUTHORITATIVE.
------------------------------------
On the statement this was built against it extracts 240 transactions where
line parsing extracted zero — but cross-checking against known transactions
showed it MISSED a ₹1,47,500 payment and a ₹5,50,000 payment, and found only
9 of 12 monthly challans. Two causes: the statement interleaves two accounts
(current and fixed deposit), so one running-balance chain does not apply; and
some rows split the date and amount differently from the anchor heuristic.

Balance continuity proves INTERNAL CONSISTENCY. It does not prove
COMPLETENESS — a self-consistent set can still be missing a third of the
statement, which is exactly what happened here.

So: use this to accelerate reading a statement, never to declare a period
reconciled. Always run cross_check() with transactions you already know are
in the period, and never mark coverage 'held' on its output alone. See
lesson L009.

Usage
-----
    python3 pdf_table.py STATEMENT.pdf              # preview
    python3 pdf_table.py STATEMENT.pdf --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
     "nov", "dec"], 1)}

DATE_RE = re.compile(
    r"\b(\d{1,2})[/-]([A-Za-z]{3})[a-z]*[/-](\d{2,4})\b"      # 16/Apr/2025
    r"|\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b"                  # 16/04/2025
)
AMOUNT_RE = re.compile(r"\d{1,3}(?:,\d{2,3})*\.\d{2}\b|\b\d+\.\d{2}\b")

# Rows that carry a date and a number but are not transactions.
NOISE_RE = re.compile(
    r"(date\s+and\s+time|lien\s+balance|available\s+balance|closing\s+balance"
    r"|opening\s+balance|statement\s+(of|period|date)|page\s+\d+\s+of"
    r"|printed\s+on|generated\s+on|grand\s+total|b/f|c/f)", re.I)


def parse_date_token(text: str) -> date | None:
    m = DATE_RE.search(text)
    if not m:
        return None
    try:
        if m.group(1):
            d, mon, y = int(m.group(1)), MONTHS.get(m.group(2).lower()[:3]), int(m.group(3))
            if not mon:
                return None
            if y < 100:
                y += 2000
            return date(y, mon, d)
        return date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
    except (ValueError, TypeError):
        return None


def parse_amount(tok: str) -> float | None:
    try:
        return float(tok.replace(",", ""))
    except ValueError:
        return None


def fragments(pdf_path: Path) -> list[tuple[int, float, float, str]]:
    """Every text fragment as (page, x, y, text)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            sys.exit("pip install pypdf")

    out: list[tuple[int, float, float, str]] = []
    reader = PdfReader(str(pdf_path))
    for pno, page in enumerate(reader.pages):
        collected: list[tuple[float, float, str]] = []

        def visitor(text, cm, tm, font, size, _c=collected):
            if text and text.strip():
                _c.append((round(tm[4], 1), round(tm[5], 1), text.strip()))

        try:
            page.extract_text(visitor_text=visitor)
        except Exception:
            continue
        for x, y, t in collected:
            out.append((pno, x, y, t))
    return out


def rows_of(frags, y_tolerance: float = 2.0) -> list[tuple[int, float, list]]:
    """Group fragments into visual rows, tolerating slight baseline drift."""
    by_page: dict[int, list] = defaultdict(list)
    for pno, x, y, t in frags:
        by_page[pno].append((x, y, t))

    rows = []
    for pno in sorted(by_page):
        buckets: dict[float, list] = defaultdict(list)
        for x, y, t in by_page[pno]:
            key = next((k for k in buckets if abs(k - y) <= y_tolerance), y)
            buckets[key].append((x, t))
        for y in sorted(buckets, reverse=True):     # top of page downwards
            rows.append((pno, y, sorted(buckets[y])))
    return rows


def extract_transactions(pdf_path: Path) -> tuple[list[dict], str | None]:
    """Return (transactions, diagnostic). Diagnostic is None on success.

    Layout of the statements seen in practice: each transaction occupies an
    ANCHOR row (serial, date, movement) plus a DETAIL row immediately below
    (reference, timestamp, narration, running balance) and any number of
    continuation rows carrying the wrapped narration.

    Columns are identified by x-position, learned from the anchors rather
    than hard-coded, so a differently-laid-out statement is detected instead
    of silently misread.
    """
    frags = fragments(pdf_path)
    if not frags:
        return [], ("no text layer — the statement is a scan and needs OCR. "
                    "It is NOT empty.")

    rows = rows_of(frags)

    # --- learn the column geometry from rows that are unambiguously anchors:
    # a date and exactly one amount, with the date left of the amount.
    amount_xs: list[float] = []
    for _, _, cells in rows:
        text = " ".join(t for _, t in cells)
        if NOISE_RE.search(text):
            continue
        if not parse_date_token(text):
            continue
        amts = [(x, parse_amount(m)) for x, t in cells for m in AMOUNT_RE.findall(t)]
        amts = [(x, a) for x, a in amts if a is not None]
        if len(amts) == 1:
            amount_xs.append(amts[0][0])

    if not amount_xs:
        dated = sum(1 for _, _, c in rows
                    if parse_date_token(" ".join(t for _, t in c)))
        moneyed = sum(1 for _, _, c in rows
                      if AMOUNT_RE.search(" ".join(t for _, t in c)))
        return [], (f"{len(rows)} rows read: {dated} carry a date, {moneyed} "
                    f"carry an amount, but no row carries a date with a single "
                    f"amount. The column layout is unrecognised — inspect the "
                    f"PDF before trusting any extraction.")

    amount_xs.sort()
    amount_col = amount_xs[len(amount_xs) // 2]      # median: robust to outliers

    txns: list[dict] = []
    current: dict | None = None

    for pno, y, cells in rows:
        text = " ".join(t for _, t in cells)
        if NOISE_RE.search(text):
            continue

        d = parse_date_token(text)
        amts = [(x, parse_amount(m)) for x, t in cells for m in AMOUNT_RE.findall(t)]
        amts = [(x, a) for x, a in amts if a is not None]

        # ANCHOR: a date plus an amount sitting in the movement column.
        in_col = [(x, a) for x, a in amts if abs(x - amount_col) < 40]
        if d and in_col:
            if current:
                txns.append(current)
            current = {
                "page": pno, "date": d, "amount": in_col[0][1],
                "balance": None, "description": "", "_parts": [],
            }
            continue

        if not current:
            continue

        # DETAIL / continuation rows. The running balance sits right of the
        # movement column, split across fragments ('3,38,067.' then '84').
        #
        # The fragments do NOT always arrive in reading order: a real row
        # emitted ['.09', '50,05,262'], which naive concatenation turned into
        # 0.845541095 instead of 50,05,262.09. So group by x-position and
        # order the pieces so the fractional part goes last.
        if current["balance"] is None:
            right = [(x, t) for x, t in cells if x > amount_col + 40]
            if right:
                by_x: dict[float, list[str]] = defaultdict(list)
                for x, t in right:
                    key = next((k for k in by_x if abs(k - x) <= 5), x)
                    by_x[key].append(t)
                for key in sorted(by_x, reverse=True):     # rightmost column
                    pieces = by_x[key]
                    # A piece starting with '.' is the decimal tail wherever
                    # it appears in the fragment stream.
                    head = [p for p in pieces if not p.startswith(".")]
                    tail = [p for p in pieces if p.startswith(".")]
                    joined = "".join(head + tail).replace(" ", "")
                    if not joined.count("."):
                        continue
                    bal = parse_amount(joined)
                    # Sanity: a running balance is not a fraction of a rupee.
                    if bal is not None and bal >= 1:
                        current["balance"] = bal
                        break

        # Narration sits between the date and the movement columns. Exclude
        # bare numbers: those are serials, reference ids and split decimals.
        for x, t in cells:
            if amount_col - 200 < x < amount_col - 20 and not re.fullmatch(r"[\d,.:\s]+", t):
                if len(current["_parts"]) < 14:
                    current["_parts"].append(t)

    if current:
        txns.append(current)

    for t in txns:
        joined = "".join(f if f.endswith("/") else f + " " for f in t["_parts"])
        t["description"] = re.sub(r"\s+", " ", joined).strip()[:500]
        t.pop("_parts", None)

    if not txns:
        return [], ("rows were read but none matched the transaction layout — "
                    "inspect the PDF before trusting any extraction.")
    return txns, None


def cross_check(txns: list[dict], expected: dict[float, str]) -> list[str]:
    """Verify that known transactions were actually found.

    Balance continuity proves internal consistency; it does NOT prove
    completeness. An extractor can produce a perfectly self-consistent set
    that is missing a third of the statement. The only test that catches
    that is looking for transactions you already know are there.
    """
    problems = []
    for amount, label in expected.items():
        if not any(abs(t["amount"] - amount) < 1.0 for t in txns):
            problems.append(f"MISSING: {label} ({amount:,.2f}) is known to be "
                            f"in this period but was not extracted")
    return problems


def sanity_check(txns: list[dict]) -> list[str]:
    """Independent checks on the result.

    Balance continuity is the strongest available: if each row's balance
    equals the previous balance plus or minus the movement, the amounts were
    read from the right columns. It is checked, never assumed.
    """
    problems = []
    if not txns:
        return ["no transactions extracted"]

    dated = [t for t in txns if t.get("date")]
    if len(dated) != len(txns):
        problems.append(f"{len(txns) - len(dated)} transaction(s) without a date")

    seq = [t for t in txns if t.get("balance") is not None
           and t.get("amount") is not None]
    breaks = 0
    for prev, cur in zip(seq, seq[1:]):
        delta = cur["balance"] - prev["balance"]
        if abs(abs(delta) - cur["amount"]) > 1.0:
            breaks += 1
    if seq and breaks:
        pct = 100.0 * breaks / max(1, len(seq) - 1)
        problems.append(
            f"balance continuity fails on {breaks} of {len(seq) - 1} "
            f"consecutive pairs ({pct:.0f}%) — amounts may be read from the "
            f"wrong column")

    order = [t["date"] for t in dated]
    if order != sorted(order):
        problems.append("dates are not in ascending order — rows may be "
                        "misgrouped")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Coordinate-aware statement extraction")
    ap.add_argument("pdf")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=15)
    args = ap.parse_args()

    path = Path(args.pdf)
    if not path.exists():
        sys.exit(f"Not found: {path}")

    txns, diag = extract_transactions(path)
    if diag:
        print(f"Could not extract from {path.name}.")
        print(f"  {diag}")
        return 1

    if args.json:
        print(json.dumps(txns, indent=2, default=str))
        return 0

    print(f"\n{path.name}: {len(txns)} transaction(s)")
    if txns:
        print(f"  {txns[0]['date']} → {txns[-1]['date']}")
    print("-" * 78)
    for t in txns[:args.limit]:
        bal = f"{t['balance']:>14,.2f}" if t["balance"] is not None else " " * 14
        print(f"  {t['date']}  {t['amount']:>12,.2f} {bal}  "
              f"{t['description'][:44]}")
    if len(txns) > args.limit:
        print(f"  … and {len(txns) - args.limit} more")

    problems = sanity_check(txns)
    print("-" * 78)
    if problems:
        print("  CHECKS FAILED — do not load this without inspecting it:")
        for p in problems:
            print(f"    ! {p}")
        return 1
    print("  Checks passed: every row dated, balances continuous, dates ordered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
