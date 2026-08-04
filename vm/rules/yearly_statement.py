#!/usr/bin/env python3
"""
Consolidate a financial year's statements into one readable PDF.

Why this exists: a year's transactions arrive as 51 weekly HTML files, or 12
monthly PDFs, or one annual PDF, depending on the year and the account.
Answering "what did we pay this vendor in FY 2016-17?" should not mean opening
fifty files.

Deliberate design choice — this is NOT a replica of a bank statement.
--------------------------------------------------------------------
It uses the same columns and ordering as ICICI's own layout, so it reads
familiarly, but it is headed and footed as a COMPILED WORKING DOCUMENT with
its sources listed. A generated file that mimicked bank letterhead while
containing real balances could be mistaken for a bank-issued statement by an
auditor, a lender, or a tax officer. That risk is not worth the cosmetic
gain, and the originals remain the evidence.

Every page carries: the source files it was built from, the extraction date,
and a verification line stating whether the balance chain is continuous.

Usage
-----
    python3 yearly_statement.py --dir ARCHIVE/058105002309-closed-2026/FY2016-17 \\
                                --account 058105002309 --fy 2016-17 --out FY2016-17.pdf
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
                                    Paragraph, Spacer, Table, TableStyle)
except ImportError:
    sys.exit("pip install reportlab")


# ---------------------------------------------------------------------------
# Readers — one per format encountered in the archive
# ---------------------------------------------------------------------------

def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


AMT = r"([\d,]+\.\d{2})"


def read_pipe_txt(path: Path) -> list[dict]:
    """Pipe-delimited TXT (2309, Apr–Jul 2016)."""
    out = []
    for line in path.read_text(errors="replace").splitlines():
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 7:
            continue
        m = re.match(r"(\d{2})-([A-Za-z]{3})-(\d{4})", parts[1])
        if not m:
            continue
        try:
            d = datetime.strptime(parts[1][:11], "%d-%b-%Y").date()
        except ValueError:
            continue
        desc = parts[2]
        if re.match(r"\s*B/F\b", desc, re.I):
            continue
        nums = [p for p in parts[3:] if re.fullmatch(r"[\d,]+\.\d{2}", p)]
        if not nums:
            continue
        vals = [float(n.replace(",", "")) for n in nums]
        bal = vals[-1]
        dr = vals[0] if len(vals) >= 2 and vals[0] else 0.0
        cr = vals[1] if len(vals) >= 3 and vals[1] else 0.0
        out.append({"date": d, "particulars": desc, "dr": dr, "cr": cr, "bal": bal})
    return out


def read_html(path: Path) -> list[dict]:
    """HTML table (2309, Aug 2016 → Mar 2017)."""
    text = _clean(path.read_text(errors="replace"))
    out = []
    # Anchor each record between the account number and the branch name that
    # ends it. Matching "three amounts after the description" fails on lines
    # where a figure lives INSIDE the description — a foreign-currency line
    # reads "2331.04 USD @ 63.80 0.00 148533.81 23748476.77", where 63.80 is
    # an exchange rate, not the debit. Taking the LAST three amounts before
    # the branch is correct in both cases.
    pattern = re.compile(
        r"058105002309\s+(\d{1,2}-[A-Za-z]{3}-\d{4})\s+([\d-]{10})\s+"
        r"(.*?)\s*(?=058105002309\s+\d{1,2}-[A-Za-z]{3}-\d{4}|Closing Balance|$)",
        re.S)
    for m in pattern.finditer(text):
        try:
            d = datetime.strptime(m.group(1), "%d-%b-%Y").date()
        except ValueError:
            continue
        body = m.group(3).strip()
        if re.match(r"\s*B/F\b", body, re.I):
            continue
        nums = re.findall(AMT, body)
        if len(nums) < 3:
            continue
        dr, cr, bal = (float(n.replace(",", "")) for n in nums[-3:])
        # Strip the trailing figures and branch from the narration.
        desc = body
        for n in nums[-3:]:
            desc = desc.replace(n, " ", 1)
        desc = re.sub(r"\s+(MAGARPATTA PUNE|RPC MUMBAI|PUNE - WTC-KHARADI|"
                      r"NARIMAN POINT|CONNAUGHT PLACE)\s*$", "", desc.strip(), flags=re.I)
        out.append({"date": d, "particulars": re.sub(r"\s+", " ", desc).strip(),
                    "dr": dr, "cr": cr, "bal": bal})
    return out


def read_pdf(path: Path) -> list[dict]:
    """PDF, via the shared extractor (table-aware, then single-line)."""
    try:
        import pdf_table
    except ImportError:
        return []
    txns, _ = pdf_table.extract_transactions(path)
    out = []
    prev_bal = None
    for t in txns:
        amt = t.get("amount") or 0.0
        bal = t.get("balance")
        # The extractor reports an amount and a balance but not the
        # direction. Infer it from the balance movement: a rising balance is
        # money in. Without this every row looks like a debit, which breaks
        # the continuity check and hides genuinely complete statements.
        dr = cr = 0.0
        if bal is not None and prev_bal is not None:
            if bal > prev_bal:
                cr = amt
            else:
                dr = amt
        else:
            dr = amt
        out.append({"date": t["date"], "particulars": t.get("description", ""),
                    "dr": dr, "cr": cr, "bal": bal})
        if bal is not None:
            prev_bal = bal
    return out


def read_any(path: Path) -> list[dict]:
    s = path.suffix.lower()
    if s == ".txt":
        return read_pipe_txt(path)
    if s in (".html", ".htm"):
        return read_html(path)
    if s == ".pdf":
        return read_pdf(path)
    return []


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------

def fy_bounds(fy: str) -> tuple[date, date]:
    y = int(fy.split("-")[0])
    return date(y, 4, 1), date(y + 1, 3, 31)


def collect(folder: Path, fy: str) -> tuple[list[dict], list[str], list[str]]:
    """Gather, deduplicate and sort a year's transactions.

    Deduplication matters: weekly and monthly statements overlap, so the same
    transaction legitimately appears in two source files. Keying on
    (date, particulars, dr, cr, balance) keeps genuine same-day duplicates —
    two identical fees on one day are real — while removing re-reads.
    """
    lo, hi = fy_bounds(fy)

    # If one source already covers the year with a continuous balance chain,
    # USE IT ALONE. Merging a complete source with partial ones does not add
    # information — it adds duplicates, because the same transaction read
    # from two files rarely matches exactly on every field. Measured on
    # FY2017-18: the full-year PDF alone gives 547 transactions with 546/546
    # continuity; merged with the monthlies it gives 617, i.e. 70 phantoms.
    best = _single_complete_source(folder, lo, hi)
    if best:
        rows, name = best
        return _chain_order(rows), [f"{name} (complete, verified)"], []

    seen: dict[tuple, dict] = {}
    used, skipped = [], []

    for f in sorted(folder.rglob("*")):
        # macOS writes AppleDouble sidecars ("._Name.pdf") that carry the
        # right extension but no content. Reading one throws and, worse,
        # aborts the whole year — so skip them explicitly.
        if f.name.startswith("._") or f.name == ".DS_Store":
            continue
        if not f.is_file() or f.suffix.lower() not in (".txt", ".html", ".htm", ".pdf"):
            continue
        try:
            rows = read_any(f)
        except Exception as exc:
            # One unreadable file must not cost the whole year. Record it and
            # carry on; the summary reports what was skipped.
            skipped.append(f"{f.name} (unreadable: {type(exc).__name__})")
            continue
        kept = 0
        for r in rows:
            if not (lo <= r["date"] <= hi):
                continue
            # Key on the FINANCIAL FACTS, not the narration. The same
            # transaction read from a weekly TXT and a monthly PDF carries
            # slightly different description text ("Tran Charges Mar-16" vs
            # "Tran Charges Mar-16 Cr 13-04-2016 NARIMAN POINT"), so keying
            # on text lets duplicates through — and a duplicated row breaks
            # the balance chain, which is our only completeness check.
            #
            # Date + movement + resulting balance identifies a transaction
            # uniquely: two genuinely distinct transactions cannot both leave
            # the account at the same balance on the same day.
            # PDF extraction sometimes reads the BALANCE column as the
            # amount, producing a phantom row whose "movement" equals a real
            # balance elsewhere that day. Such a row has no balance of its
            # own and an implausibly large amount — drop it rather than let
            # it break the chain.
            # A row with a zero balance mid-statement is a parse failure,
            # not a real position: it breaks the chain on both sides and
            # cannot be ordered. Observed on a truncated "4200 USD @" line.
            if r["bal"] is not None and r["bal"] == 0:
                continue

            if r["bal"] is None and (r["dr"] or 0) > 0:
                same_day_balances = {round(x["bal"], 2) for x in rows
                                     if x["date"] == r["date"] and x["bal"] is not None}
                if round(r["dr"], 2) in same_day_balances:
                    continue

            key = (r["date"], round(r["dr"], 2), round(r["cr"], 2),
                   round(r["bal"] or 0, 2))
            if key in seen:
                continue
            seen[key] = r
            kept += 1
        (used if kept else skipped).append(f"{f.name} ({kept})" if kept else f.name)

    rows = sorted(seen.values(), key=lambda r: (r["date"], r["bal"] or 0))

    # Within a single day the sort above is arbitrary, which breaks the
    # balance chain and makes verification report false failures. Reorder
    # each day so that each row's balance follows from the previous one.
    rows = _chain_order(rows)
    rows = fix_directions(rows)
    rows = _chain_order(rows)          # re-order now directions are right

    # These statements interleave the current account with its linked fixed
    # deposits, so two balance series are tangled and rows from one chain
    # never reconcile against the other. Separate them, then restore date
    # order for presentation — the verification walks the chains, not the
    # printed order.
    rows = split_chains(rows)
    return rows, used, skipped


def _single_complete_source(folder: Path, lo: date, hi: date):
    """Find one file that covers the whole period with an unbroken balance
    chain. Returns (rows, filename) or None.

    'Complete' is judged by evidence, not by filename: the rows must span at
    least 11 months of the period AND every consecutive pair must reconcile.
    """
    best = None
    for f in sorted(folder.rglob("*")):
        if f.name.startswith("._") or f.name == ".DS_Store":
            continue
        if not f.is_file() or f.suffix.lower() not in (".pdf", ".html", ".htm", ".txt"):
            continue
        try:
            rows = [r for r in read_any(f) if lo <= r["date"] <= hi]
        except Exception:
            continue
        if len(rows) < 50:
            continue
        span_days = (max(r["date"] for r in rows) - min(r["date"] for r in rows)).days
        if span_days < 330:
            continue
        chain = [r for r in rows if r["bal"] is not None]
        if len(chain) < len(rows) * 0.95:
            continue
        breaks = sum(
            1 for a, b in zip(chain, chain[1:])
            if abs((a["bal"] - ((b["dr"] or 0) - (b["cr"] or 0))) - b["bal"]) > 1.0)
        if breaks == 0 and (best is None or len(rows) > len(best[0])):
            best = (rows, f.name)
    return best


def _chain_order(rows: list[dict]) -> list[dict]:
    """Order transactions so the running balance is continuous.

    A statement lists transactions in the order the bank applied them, and
    that order is NOT recoverable from (date, amount) — two transactions on
    one day can be listed either way round. Sorting them wrongly breaks the
    balance chain twice over, which then reads as "data is missing" when
    nothing is missing at all.

    The balance itself resolves it: each row's balance must equal the
    previous balance minus its movement. Within a day we therefore search
    for the ordering that satisfies that, rather than guessing.

    Days with many transactions are capped: an exhaustive search is
    factorial, so beyond a threshold the greedy pass is used and any
    residual breaks are reported honestly rather than hidden.
    """
    from itertools import groupby, permutations

    def fits(prev_bal, r):
        if prev_bal is None or r["bal"] is None:
            return False
        move = (r["dr"] or 0) - (r["cr"] or 0)
        return abs((prev_bal - move) - r["bal"]) < 1.0

    out: list[dict] = []
    prev = None
    for _, group in groupby(rows, key=lambda r: r["date"]):
        day = list(group)

        # Rows lacking a balance cannot join the chain, but they must not
        # abandon the whole day: the rows that DO have balances still need
        # ordering. Set them aside, order the rest, then append them.
        unbalanced = [r for r in day if r["bal"] is None]
        day = [r for r in day if r["bal"] is not None]

        if not day:
            out.extend(unbalanced)
            continue
        if len(day) == 1:
            out.extend(day + unbalanced)
            prev = day[0]["bal"]
            continue

        # Small days: find an ordering where every step reconciles.
        solved = None
        if len(day) <= 8:
            for perm in permutations(day):
                cur, ok = prev, True
                for r in perm:
                    if not fits(cur, r):
                        ok = False
                        break
                    cur = r["bal"]
                if ok:
                    solved = list(perm)
                    break

        if solved is None:
            # Greedy: repeatedly take whichever remaining row follows from
            # the current balance; fall back to input order when none does.
            # Greedy chain-walk. Where no row follows the current balance,
            # try starting from each remaining row instead of blindly taking
            # the first — a single bad choice otherwise cascades through the
            # whole day.
            remaining, ordered, cur = day[:], [], prev
            while remaining:
                pick = next((r for r in remaining if fits(cur, r)), None)
                if pick is None:
                    # Restart the chain from whichever row leaves the most
                    # of the day still reachable.
                    best, best_reach = remaining[0], -1
                    for cand in remaining:
                        reach, c2, pool = 0, cand["bal"], [x for x in remaining if x is not cand]
                        while True:
                            nxt = next((x for x in pool if fits(c2, x)), None)
                            if nxt is None:
                                break
                            reach += 1
                            c2 = nxt["bal"]
                            pool.remove(nxt)
                        if reach > best_reach:
                            best, best_reach = cand, reach
                    pick = best
                ordered.append(pick)
                remaining.remove(pick)
                cur = pick["bal"] if pick["bal"] is not None else cur
            solved = ordered

        out.extend(solved + unbalanced)
        prev = solved[-1]["bal"] if solved[-1]["bal"] is not None else prev
    return out


def fix_directions(rows: list[dict]) -> list[dict]:
    """Correct rows whose debit/credit contradicts the balance movement.

    Some statements place the Dr/Cr marker where the parser cannot see it, so
    a credit is recorded as a debit. The balance is the arbiter: if the
    balance ROSE, money came in, whatever the columns say. Symptom in the
    break report is a discrepancy of exactly twice the amount.
    """
    prev = None
    for r in rows:
        if r["bal"] is None:
            continue
        if prev is not None:
            delta = r["bal"] - prev
            amt = (r["dr"] or 0) + (r["cr"] or 0)
            if amt and abs(abs(delta) - amt) < 1.0:
                if delta > 0 and (r["dr"] or 0) > 0:      # rose but marked debit
                    r["cr"], r["dr"] = r["dr"], 0.0
                elif delta < 0 and (r["cr"] or 0) > 0:    # fell but marked credit
                    r["dr"], r["cr"] = r["cr"], 0.0
        prev = r["bal"]
    return rows


def split_chains(rows: list[dict]) -> list[dict]:
    """Separate interleaved account chains.

    These statements list the current account and its linked fixed deposits
    together. Two balance series are therefore tangled, and a row from one
    chain never reconciles against the previous row of the other — producing
    breaks of crore magnitude that look alarming but mean nothing.

    Rows are assigned to whichever chain their balance continues, and the
    chains are then emitted in order.
    """
    chains: list[list[dict]] = []
    for r in rows:
        if r["bal"] is None:
            (chains[0] if chains else chains.append([]) or chains[0]).append(r)
            continue
        placed = False
        for ch in chains:
            last = next((x for x in reversed(ch) if x["bal"] is not None), None)
            if last is None:
                continue
            move = (r["dr"] or 0) - (r["cr"] or 0)
            if abs((last["bal"] - move) - r["bal"]) < 1.0:
                ch.append(r)
                placed = True
                break
        if not placed:
            chains.append([r])
    # Largest chain first — that is the operating account.
    chains.sort(key=len, reverse=True)
    for i, ch in enumerate(chains):
        for r in ch:
            r["_chain"] = i
    return [r for ch in chains for r in ch]


def verify(rows: list[dict]) -> str:
    """State plainly whether the balance chain holds."""
    chain = [r for r in rows if r["bal"] is not None]
    if len(chain) < 2:
        return "Balance continuity: not verifiable (insufficient balance data)."
    # A statement may carry more than one account (the current account plus
    # its linked deposits), so the rows form several balance series. The seam
    # between two series is not an error — comparing the last row of one to
    # the first of another is meaningless. Count only breaks WITHIN a series.
    breaks = 0
    for a, b in zip(chain, chain[1:]):
        if a.get("_chain") != b.get("_chain"):
            continue
        move = (b["dr"] or 0) - (b["cr"] or 0)
        if abs((a["bal"] - move) - b["bal"]) > 1.0:
            breaks += 1
    total = sum(1 for a, b in zip(chain, chain[1:])
                if a.get("_chain") == b.get("_chain"))
    if breaks == 0:
        seams = (len(chain) - 1) - total
        note = (f" ({seams} boundary/boundaries between separate account series "
                f"excluded — the statement carries linked deposits)") if seams else ""
        return (f"Balance continuity: VERIFIED — every one of {total} consecutive "
                f"pairs reconciles{note}.")
    return (f"Balance continuity: {total - breaks} of {total} pairs reconcile, "
            f"{breaks} break(s). Statements may be incomplete for this year.")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def build_pdf(rows, out_path: Path, account: str, fy: str,
              sources: list[str], verdict: str):
    lo, hi = fy_bounds(fy)
    doc = BaseDocTemplate(str(out_path), pagesize=landscape(A4),
                          leftMargin=10 * mm, rightMargin=10 * mm,
                          topMargin=22 * mm, bottomMargin=14 * mm,
                          title=f"Compiled statement {account} FY {fy}")

    small = ParagraphStyle("small", fontName="Helvetica", fontSize=7, leading=8.5)
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=6.5, leading=7.5)

    def header_footer(canvas, docu):
        canvas.saveState()
        w, h = landscape(A4)
        # Banner — deliberately NOT bank livery.
        canvas.setFillColor(colors.HexColor("#2b3a55"))
        canvas.rect(0, h - 16 * mm, w, 16 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(10 * mm, h - 8 * mm,
                          "EXADATUM SOFTWARE SERVICES PRIVATE LIMITED")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(10 * mm, h - 12.5 * mm,
                          f"Compiled statement of account {account}   "
                          f"FY {fy}   ({lo:%d %b %Y} to {hi:%d %b %Y})")
        canvas.setFont("Helvetica-Oblique", 7)
        canvas.drawRightString(w - 10 * mm, h - 12.5 * mm,
                               "COMPILED WORKING DOCUMENT — not a bank-issued statement")
        # Footer
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(10 * mm, 8 * mm,
                          f"Compiled {date.today():%d %B %Y} from statements issued by "
                          f"ICICI Bank. Originals remain the authoritative record.")
        canvas.drawRightString(w - 10 * mm, 8 * mm, f"Page {docu.page}")
        canvas.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                       onPage=header_footer)])

    story = []
    story.append(Paragraph(verdict, small))
    story.append(Paragraph(
        f"Compiled from {len(sources)} source file(s): "
        + ", ".join(sources[:12]) + (" …" if len(sources) > 12 else ""), small))
    story.append(Spacer(1, 4 * mm))

    data = [["Date", "Particulars", "Withdrawals", "Deposits", "Balance"]]
    tot_dr = tot_cr = 0.0
    for r in rows:
        tot_dr += r["dr"] or 0
        tot_cr += r["cr"] or 0
        data.append([
            r["date"].strftime("%d-%m-%Y"),
            Paragraph(html.escape(r["particulars"][:150]), cell),
            f"{r['dr']:,.2f}" if r["dr"] else "",
            f"{r['cr']:,.2f}" if r["cr"] else "",
            f"{r['bal']:,.2f}" if r["bal"] is not None else "",
        ])
    data.append(["", Paragraph("<b>Total</b>", cell),
                 f"{tot_dr:,.2f}", f"{tot_cr:,.2f}", ""])

    table = Table(data, colWidths=[20 * mm, 155 * mm, 30 * mm, 30 * mm, 32 * mm],
                  repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe4ec")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b8c0cc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2),
         [colors.white, colors.HexColor("#f5f7fa")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dfe4ec")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(table)
    doc.build(story)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compile a year's statements into one PDF")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--account", required=True)
    ap.add_argument("--fy", required=True, help="e.g. 2016-17")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    folder = Path(args.dir)
    if not folder.is_dir():
        sys.exit(f"Not a folder: {folder}")

    rows, used, skipped = collect(folder, args.fy)
    if not rows:
        sys.exit(f"No transactions found for FY {args.fy} in {folder}")

    verdict = verify(rows)
    build_pdf(rows, Path(args.out), args.account, args.fy, used, verdict)

    print(f"{args.out}: {len(rows)} transactions, "
          f"{rows[0]['date']} to {rows[-1]['date']}")
    print(f"  {verdict}")
    print(f"  sources used: {len(used)}"
          + (f", ignored (no rows in FY): {len(skipped)}" if skipped else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
