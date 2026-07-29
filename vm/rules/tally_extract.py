#!/usr/bin/env python3
"""
Extract the books from Tally into the knowledge base.

Runs ON the VM: the XML gateway only answers on localhost while TallyPrime is
open with the company loaded.

A warning learned the hard way, kept here because it produced a wrong
conclusion earlier: **report IDs such as "Day Book" and "Ledger Vouchers"
ignore SVFROMDATE/SVTODATE in some Tally builds**, returning the same cached
response for every date range. Querying one bank ledger that way suggested
only ~96 vouchers existed across a decade; a Voucher COLLECTION for a single
year returned 2,757. Always use a collection with an explicit date range, and
treat identical byte counts across different periods as a red flag.

Usage (on the VM)
-----------------
    python tally_extract.py --fy 2025-26
    python tally_extract.py --all          # every year with data
    python tally_extract.py --masters      # ledgers and groups only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

GATEWAY = os.environ.get("TALLY_URL", "http://localhost:9000")
DSN = os.environ.get("MUNSHI_KB_DSN", "postgresql://postgres@localhost/munshi_kb")

try:
    import psycopg
except ImportError:
    psycopg = None


def post(xml: str, timeout: int = 300) -> str:
    req = urllib.request.Request(GATEWAY, data=xml.encode("utf-8"),
                                 headers={"Content-Type": "text/xml"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def company_name() -> str:
    """The loaded company's exact name, needed to scope period requests."""
    xml = post(collection("Cmp", "Company", ["Name", "BooksFrom"]), timeout=60)
    m = re.search(r'<COMPANY NAME="([^"]+)"', xml)
    return re.sub("&amp;", "&", m.group(1)) if m else ""


def collection(name: str, ctype: str, methods: list[str],
               frm: str = "", to: str = "", company: str = "") -> str:
    """A Collection scoped to a period.

    SVFROMDATE/SVTODATE alone are NOT enough. Tally answers from its *current
    period*, so a request for 2010-2027 returned only FY2025-26 — making a
    decade of books look missing when they were merely out of period. Adding
    SVCURRENTCOMPANY and SVCURRENTDATE makes Tally actually move its reporting
    period, at which point FY2019-20 returned 3,106 vouchers instead of zero.
    """
    static = "<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
    if company:
        static += f"<SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>"
    if frm:
        static += (f'<SVFROMDATE TYPE="Date">{frm}</SVFROMDATE>'
                   f'<SVTODATE TYPE="Date">{to}</SVTODATE>'
                   f'<SVCURRENTDATE TYPE="Date">{to}</SVCURRENTDATE>')
    native = "".join(f"<NATIVEMETHOD>{m}</NATIVEMETHOD>" for m in methods)
    return (f'<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>'
            f'<TYPE>Collection</TYPE><ID>{name}</ID></HEADER><BODY><DESC>'
            f'<STATICVARIABLES>{static}</STATICVARIABLES><TDL><TDLMESSAGE>'
            f'<COLLECTION NAME="{name}" ISMODIFY="No"><TYPE>{ctype}</TYPE>'
            f'{native}</COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>')


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

TAG = re.compile(r"<([A-Z0-9.]+)>(.*?)</\1>", re.S)


def unescape(s: str) -> str:
    """Tally emits XML entities; store the human-readable form.

    Left as text, ledgers read as 'ARTH &amp; Associates' and, worse, a search
    for "ARTH & Associates" fails to match its own ledger.
    """
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&apos;", "'"), ("&#39;", "'")):
        s = s.replace(a, b)
    return s


def tag_text(block: str, name: str) -> str:
    """Read a tag's text.

    Tally decorates tags with attributes — `<DATE TYPE="Date">`,
    `<NARRATION TYPE="String">` — so the opening tag must allow them. A regex
    requiring a bare `<DATE>` silently matches nothing, which drops every
    voucher rather than failing loudly.
    """
    m = re.search(rf"<{name}(?:\s[^>]*)?>(.*?)</{name}>", block, re.S)
    if not m:
        return ""
    return unescape(
        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip())


def parse_date(s: str) -> date | None:
    s = (s or "").strip()
    for fmt in ("%Y%m%d", "%d-%b-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:11] if "-" in s else s[:8], fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(s: str) -> float | None:
    s = re.sub(r"[₹,\s]", "", s or "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# Requires at least one attribute, so the response header's own
# `<VOUCHER>0</VOUCHER>` counter tag cannot masquerade as a voucher. Real
# vouchers always carry REMOTEID/VCHKEY/VCHTYPE.
VOUCHER_RE = re.compile(r"<VOUCHER\s[^>]*>(.*?)</VOUCHER>", re.S)

# Entry lists nest: BILLALLOCATIONS.LIST etc. carry their own AMOUNT tags,
# which would otherwise be mistaken for the entry's amount.
NESTED_LIST_RE = re.compile(r"<[A-Z0-9.]+\.LIST[^>]*>.*?</[A-Z0-9.]+\.LIST>", re.S)


def parse_vouchers(xml: str) -> list[dict]:
    """One dict per voucher, with its ledger entries."""
    out = []
    for m in VOUCHER_RE.finditer(xml):
        b = m.group(1)
        if tag_text(b, "ISDELETED").upper() == "YES":
            continue
        d = parse_date(tag_text(b, "DATE"))
        if not d:
            continue
        entries = []
        for em in re.finditer(
                r"<ALLLEDGERENTRIES\.LIST[^>]*>(.*?)</ALLLEDGERENTRIES\.LIST>",
                b, re.S):
            eb = NESTED_LIST_RE.sub("", em.group(1))
            led = tag_text(eb, "LEDGERNAME")
            amt = parse_amount(tag_text(eb, "AMOUNT"))
            if not led or amt is None:
                continue
            # Tally states direction explicitly: ISDEEMEDPOSITIVE=Yes means
            # debit. The AMOUNT sign normally agrees (negative for debits), but
            # the two can disagree, and that disagreement is meaningful — a
            # *negative credit* is a contra line that must SUBTRACT from its
            # side. Forex revaluation on the EEFC account does exactly this:
            # 725,064.48 credit less an 11,204.00 negative credit balances the
            # 713,860.48 debit. Taking abs() here turned that subtraction into
            # an addition and made 22 sound vouchers look broken.
            deemed = tag_text(eb, "ISDEEMEDPOSITIVE").upper()
            is_debit = (deemed == "YES") if deemed else (amt < 0)
            magnitude = -abs(amt) if (is_debit != (amt < 0)) else abs(amt)
            entries.append({"ledger": led, "amount": magnitude,
                            "is_debit": is_debit})
        out.append({
            "date": d,
            "type": tag_text(b, "VOUCHERTYPENAME") or m.group(0)[:200],
            "number": tag_text(b, "VOUCHERNUMBER"),
            "party": tag_text(b, "PARTYLEDGERNAME"),
            "narration": tag_text(b, "NARRATION"),
            "entries": entries,
        })
    return out


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def fy_of(d: date) -> str:
    return f"{d.year}-{str(d.year+1)[2:]}" if d.month >= 4 else f"{d.year-1}-{str(d.year)[2:]}"


def voucher_hash(v: dict) -> str:
    total = sum(abs(e["amount"]) for e in v["entries"])
    blob = f"{v['date']}|{v['type']}|{v['number']}|{v['party']}|{total:.2f}|{v['narration'][:100]}"
    return hashlib.sha256(blob.encode()).hexdigest()


def load(conn, vouchers: list[dict]) -> tuple[int, int]:
    added = skipped = 0
    with conn.cursor() as cur:
        for v in vouchers:
            h = voucher_hash(v)
            cur.execute("SELECT 1 FROM tally_voucher WHERE row_hash=%s", (h,))
            if cur.fetchone():
                skipped += 1
                continue
            cur.execute(
                """INSERT INTO tally_voucher
                   (voucher_date, voucher_type, voucher_number, narration,
                    fin_year, row_hash)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                (v["date"], v["type"], v["number"],
                 (v["narration"] or v["party"])[:2000], fy_of(v["date"]), h))
            vid = cur.fetchone()[0]
            for e in v["entries"]:
                cur.execute(
                    """INSERT INTO tally_entry
                       (voucher_id, ledger_name, amount, is_debit)
                       VALUES (%s,%s,%s,%s)""",
                    (vid, e["ledger"][:500], e["amount"], e["is_debit"]))
            added += 1
    conn.commit()
    return added, skipped


def load_ledgers(conn, xml: str) -> int:
    n = 0
    with conn.cursor() as cur:
        for m in re.finditer(r'<LEDGER NAME="([^"]+)"[^>]*>(.*?)</LEDGER>', xml, re.S):
            name = unescape(m.group(1))[:500]
            parent = tag_text(m.group(2), "PARENT")[:500]
            cur.execute(
                """INSERT INTO tally_ledger (name, parent) VALUES (%s,%s)
                   ON CONFLICT (name) DO UPDATE SET parent=EXCLUDED.parent""",
                (name, parent))
            n += 1
    conn.commit()
    return n


VOUCHER_METHODS = ["Date", "VoucherTypeName", "VoucherNumber",
                   "PartyLedgerName", "Narration", "Amount",
                   "AllLedgerEntries.List"]


def check_balanced(vouchers: list[dict]) -> tuple[int, list[dict]]:
    """Double-entry check: debits must equal credits within each voucher.

    This is the real proof the parse is faithful. A regex that merely returns
    rows can still be wrong; a voucher whose sides disagree means entries were
    dropped, doubled, or misread — so imbalance is a parser bug until shown
    otherwise, not a data-quality observation.
    """
    bad = []
    for v in vouchers:
        if not v["entries"]:
            continue
        dr = sum(e["amount"] for e in v["entries"] if e["is_debit"])
        cr = sum(e["amount"] for e in v["entries"] if not e["is_debit"])
        if abs(dr - cr) > 0.05:
            bad.append({"date": str(v["date"]), "type": v["type"],
                        "number": v["number"], "dr": round(dr, 2),
                        "cr": round(cr, 2)})
    return len(vouchers) - len(bad), bad


def extract_year(conn, fy: str, verbose: bool = False, company: str = "") -> dict:
    y = int(fy.split("-")[0])
    xml = post(collection("Vch", "Voucher", VOUCHER_METHODS,
                          f"{y}0401", f"{y+1}0331", company=company))
    vouchers = parse_vouchers(xml)
    # The gateway sometimes ignores the date range. Trust the voucher dates,
    # not the request, and keep only what really falls in the year.
    lo, hi = date(y, 4, 1), date(y + 1, 3, 31)
    in_range = [v for v in vouchers if lo <= v["date"] <= hi]
    ok, bad = check_balanced(in_range)
    if bad and verbose:
        for b in bad[:5]:
            print(f"      UNBALANCED {b['date']} {b['type']} #{b['number']}: "
                  f"Dr {b['dr']} vs Cr {b['cr']}")
    added, skipped = load(conn, in_range) if conn else (0, 0)
    return {"fy": fy, "parsed": len(vouchers), "in_range": len(in_range),
            "balanced": ok, "unbalanced": len(bad), "added": added,
            "skipped": skipped, "bytes": len(xml)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract Tally into the knowledge base")
    ap.add_argument("--fy", help="e.g. 2025-26")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--masters", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="parse but do not load")
    args = ap.parse_args()

    conn = None
    if not args.dry_run:
        if psycopg is None:
            sys.exit("psycopg not installed")
        conn = psycopg.connect(DSN)

    company = company_name()
    print(f"company: {company or '(none reported)'}")

    if args.masters or args.all:
        xml = post(collection("Led", "Ledger", ["Name", "Parent", "OpeningBalance"]))
        n = load_ledgers(conn, xml) if conn else len(re.findall(r'<LEDGER NAME=', xml))
        print(f"ledgers: {n}")

    years = [args.fy] if args.fy else (
        [f"{y}-{str(y+1)[2:]}" for y in range(2016, 2027)] if args.all else [])
    if not years and not (args.masters):
        ap.error("give --fy, --all or --masters")

    if conn and years:
        # tally_voucher.fin_year is a foreign key into fin_year.
        with conn.cursor() as cur:
            for fy in years:
                y = int(fy.split("-")[0])
                cur.execute(
                    """INSERT INTO fin_year (label, starts_on, ends_on)
                       VALUES (%s,%s,%s) ON CONFLICT (label) DO NOTHING""",
                    (fy, date(y, 4, 1), date(y + 1, 3, 31)))
        conn.commit()

    total = unbalanced = 0
    for fy in years:
        try:
            r = extract_year(conn, fy, verbose=True, company=company)
        except Exception as e:
            print(f"  FY{fy}: ERROR {type(e).__name__}: {e}")
            continue
        total += r["added"]
        unbalanced += r["unbalanced"]
        flag = "  <-- UNBALANCED" if r["unbalanced"] else ""
        print(f"  FY{fy}: {r['in_range']:5} in range, {r['added']:5} new, "
              f"{r['skipped']:5} already held, "
              f"{r['balanced']:5} balanced{flag}")
    if years:
        print(f"total new vouchers: {total}")
        if unbalanced:
            print(f"WARNING: {unbalanced} vouchers do not balance — "
                  f"treat as a parser bug until explained")

    if conn:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
