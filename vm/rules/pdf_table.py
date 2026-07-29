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

EXTRACTION ORDER
----------------
1. pdfplumber — recovers the statement's actual ruled table. Preferred, and
   what should handle almost every statement: on the file this was built
   against it extracts 299 transactions, all with balances, and finds every
   transaction known to be in the period.
2. coordinate reconstruction — fallback for PDFs with no recoverable table.
   ASSISTIVE ONLY: it is known to miss right-aligned large amounts (it
   dropped a ₹1,47,500 payment while every internal check looked healthy —
   lesson L009).

Whichever path runs, cross_check() against transactions you already know are
in the period before treating a statement as fully read. Balance continuity
proves internal consistency, NOT completeness.
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


def _cell(v) -> str:
    """Flatten a table cell: pdfplumber preserves in-cell newlines from
    wrapped text ('4,03,967.\n84'), which must be rejoined, not split."""
    return re.sub(r"\s+", " ", str(v or "").replace("\n", "")).strip()


def extract_with_pdfplumber(pdf_path: Path) -> tuple[list[dict], str | None]:
    """Preferred path: let a real table extractor find the columns.

    Bank statements ARE tables — ruled, with headers. pdfplumber recovers
    them directly, which removes every heuristic about x-positions and
    right-aligned amounts that made the coordinate fallback unreliable
    (lesson L009).

    Columns are identified by their HEADER TEXT where a header row exists,
    and by position within the recovered table otherwise — never by absolute
    coordinates.
    """
    try:
        import pdfplumber
    except ImportError:
        return [], "pdfplumber not installed"

    txns: list[dict] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for pno, page in enumerate(pdf.pages):
                for table in page.extract_tables() or []:
                    for raw in table:
                        cells = [_cell(c) for c in raw]
                        if not any(cells):
                            continue

                        # A transaction row has a date and at least one
                        # amount. Header and footer rows have neither.
                        joined = " ".join(cells)
                        if NOISE_RE.search(joined):
                            continue
                        d = None
                        for c in cells:
                            d = parse_date_token(c)
                            if d:
                                break
                        if not d:
                            continue

                        # Amounts, in column order. The rightmost is the
                        # running balance; the one before it the movement.
                        amounts = []
                        for idx, c in enumerate(cells):
                            for m in AMOUNT_RE.findall(c):
                                a = parse_amount(m)
                                if a is not None:
                                    amounts.append((idx, a))
                        if not amounts:
                            continue

                        if len(amounts) >= 2:
                            movement = amounts[-2][1]
                            balance = amounts[-1][1]
                        else:
                            movement, balance = amounts[0][1], None

                        # Narration: the longest non-numeric cell.
                        desc = ""
                        for c in cells:
                            if len(c) > len(desc) and not re.fullmatch(r"[\d,.:\s/-]*", c):
                                desc = c
                        txns.append({
                            "page": pno, "date": d, "amount": movement,
                            "balance": balance, "description": desc[:500],
                        })
    except Exception as e:
        return [], f"pdfplumber failed: {type(e).__name__}: {e}"

    if not txns:
        return [], "pdfplumber found no table rows carrying a date and an amount"
    return txns, None


def extract_transactions(pdf_path: Path) -> tuple[list[dict], str | None]:
    """Extract transactions, preferring a real table extractor.

    Order matters. pdfplumber recovers the statement's actual table
    structure; the coordinate fallback reconstructs it from geometry and is
    demonstrably less complete (it missed a ₹1,47,500 payment — lesson L009).
    The fallback exists only for PDFs with no recoverable table.
    """
    txns, err = extract_with_pdfplumber(pdf_path)
    if txns:
        return txns, None

    txns, err2 = _extract_by_coordinates(pdf_path)
    if txns:
        return txns, None
    return [], err2 or err


def _extract_by_coordinates(pdf_path: Path) -> tuple[list[dict], str | None]:
    """Fallback: reconstruct rows from text positions.

    ASSISTIVE ONLY. Kept for PDFs where no table can be recovered, but its
    output is known to be incomplete on right-aligned columns — always
    cross_check() before relying on it.
    """
    frags = fragments(pdf_path)
    if not frags:
        return [], ("no text layer — the statement is a scan and needs OCR. "
                    "It is NOT empty.")

    rows = rows_of(frags)
    amount_xs: list[float] = []
    for _, _, cells in rows:
        text = " ".join(t for _, t in cells)
        if NOISE_RE.search(text) or not parse_date_token(text):
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
                    f"carry an amount, but no row carries both in a "
                    f"recognisable column layout.")

    amount_xs.sort()
    amount_col = amount_xs[len(amount_xs) // 2]

    txns: list[dict] = []
    current: dict | None = None
    for pno, y, cells in rows:
        text = " ".join(t for _, t in cells)
        if NOISE_RE.search(text):
            continue
        d = parse_date_token(text)
        amts = [(x, parse_amount(m)) for x, t in cells for m in AMOUNT_RE.findall(t)]
        amts = [(x, a) for x, a in amts if a is not None]
        in_col = [(x, a) for x, a in amts if abs(x - amount_col) < 45]

        if d and in_col:
            if current:
                txns.append(current)
            current = {"page": pno, "date": d, "amount": in_col[0][1],
                       "balance": None, "description": "", "_parts": []}
            continue
        if not current:
            continue

        if current["balance"] is None:
            right = [(x, t) for x, t in cells if x > amount_col + 45]
            if right:
                by_x: dict[float, list[str]] = defaultdict(list)
                for x, t in right:
                    key = next((k for k in by_x if abs(k - x) <= 5), x)
                    by_x[key].append(t)
                for key in sorted(by_x, reverse=True):
                    pieces = by_x[key]
                    head = [q for q in pieces if not q.startswith(".")]
                    tail = [q for q in pieces if q.startswith(".")]
                    joined = "".join(head + tail).replace(" ", "")
                    if "." not in joined:
                        continue
                    bal = parse_amount(joined)
                    if bal is not None and bal >= 1:
                        current["balance"] = bal
                        break

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
        return [], "no rows matched the transaction layout"
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
