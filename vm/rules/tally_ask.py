#!/usr/bin/env python3
"""
Answer questions about the company's books.

Every answer is computed from the extracted Tally data with SQL. Nothing is
inferred or recalled — if the books do not contain it, the answer is "not in
the books", which is itself useful information.

Design rule, learned twice this project: **never let an empty result stand in
for a fact**. A query that returns nothing may mean "it didn't happen" or "you
asked wrong". Where the distinction matters, the command says which.

Usage
-----
    python tally_ask.py overview
    python tally_ask.py ledger "ARTH"           # search + running total by year
    python tally_ask.py vendor "ARTH"           # everything paid to a party
    python tally_ask.py year 2019-20            # a year in summary
    python tally_ask.py tds                     # TDS ledgers across all years
    python tally_ask.py search "rent"           # narration search
    python tally_ask.py sql "SELECT ..."        # read-only escape hatch
"""

from __future__ import annotations

import os
import re
import sys
import textwrap

DSN = os.environ.get("MUNSHI_KB_DSN", "postgresql://postgres@localhost/munshi_kb")

try:
    import psycopg
except ImportError:
    sys.exit("psycopg not installed")


def rupees(x) -> str:
    """Indian digit grouping: 1,23,45,678.90"""
    if x is None:
        return "-"
    neg = x < 0
    s = f"{abs(float(x)):.2f}"
    whole, dec = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        whole = f"{head},{tail}"
    return f"{'-' if neg else ''}{whole}.{dec}"


def table(rows, headers) -> str:
    if not rows:
        return "  (nothing)"
    cols = [[str(h)] + [str(r[i]) for r in rows] for i, h in enumerate(headers)]
    w = [max(len(c) for c in col) for col in cols]
    num = [all(re.fullmatch(r"-?[\d,]*\.?\d*", c or "") for c in col[1:])
           for col in cols]
    out = ["  " + "  ".join(h.ljust(w[i]) for i, h in enumerate(headers)),
           "  " + "  ".join("-" * w[i] for i in range(len(headers)))]
    for r in rows:
        out.append("  " + "  ".join(
            (str(v).rjust(w[i]) if num[i] else str(v).ljust(w[i]))
            for i, v in enumerate(r)))
    return "\n".join(out)


def q(conn, sql, args=()) -> list:
    with conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


# ---------------------------------------------------------------------------

def cmd_overview(conn, _):
    print("THE BOOKS AT A GLANCE\n")
    rows = q(conn, """
        SELECT v.fin_year,
               COUNT(*) AS vouchers,
               COUNT(*) FILTER (WHERE v.voucher_type='Payment')  AS payments,
               COUNT(*) FILTER (WHERE v.voucher_type='Receipt')  AS receipts,
               COUNT(*) FILTER (WHERE v.voucher_type='Journal')  AS journals,
               MIN(v.voucher_date) AS first, MAX(v.voucher_date) AS last
        FROM tally_voucher v GROUP BY v.fin_year ORDER BY v.fin_year""")
    print(table([(r[0], r[1], r[2], r[3], r[4], str(r[5]), str(r[6]))
                 for r in rows],
                ["FY", "vouchers", "payments", "receipts", "journals",
                 "first", "last"]))
    tot = q(conn, "SELECT COUNT(*) FROM tally_voucher")[0][0]
    led = q(conn, "SELECT COUNT(*) FROM tally_ledger")[0][0]
    ent = q(conn, "SELECT COUNT(*) FROM tally_entry")[0][0]
    print(f"\n  {tot} vouchers, {ent} ledger entries, {led} ledgers.")

    bad = q(conn, """
        SELECT COUNT(*) FROM (
          SELECT voucher_id FROM tally_entry GROUP BY voucher_id
          HAVING ABS(SUM(CASE WHEN is_debit THEN amount ELSE -amount END))>0.05
        ) t""")[0][0]
    print(f"  Double-entry check: {'ALL BALANCE' if not bad else str(bad)+' UNBALANCED'}")


def cmd_year(conn, args):
    fy = args[0]
    print(f"FY {fy}\n")
    rows = q(conn, """
        SELECT voucher_type, COUNT(*),
               SUM((SELECT SUM(amount) FROM tally_entry e
                    WHERE e.voucher_id=v.id AND e.is_debit))
        FROM tally_voucher v WHERE fin_year=%s
        GROUP BY voucher_type ORDER BY 2 DESC""", (fy,))
    if not rows:
        print(f"  No vouchers for {fy}. Either the year has no entries, or it "
              f"was never extracted — run tally_extract.py --fy {fy}.")
        return
    print(table([(r[0], r[1], rupees(r[2])) for r in rows],
                ["type", "count", "total debits"]))
    print("\n  Busiest ledgers:")
    rows = q(conn, """
        SELECT e.ledger_name, COUNT(*),
               SUM(CASE WHEN e.is_debit THEN e.amount ELSE 0 END),
               SUM(CASE WHEN NOT e.is_debit THEN e.amount ELSE 0 END)
        FROM tally_entry e JOIN tally_voucher v ON v.id=e.voucher_id
        WHERE v.fin_year=%s GROUP BY e.ledger_name
        ORDER BY COUNT(*) DESC LIMIT 20""", (fy,))
    print(table([(r[0][:46], r[1], rupees(r[2]), rupees(r[3])) for r in rows],
                ["ledger", "entries", "debit", "credit"]))


def cmd_ledger(conn, args):
    term = args[0]
    names = q(conn, """
        SELECT DISTINCT e.ledger_name FROM tally_entry e
        WHERE e.ledger_name ILIKE %s ORDER BY 1""", (f"%{term}%",))
    if not names:
        print(f"  No ledger matching '{term}' has any entry.")
        # An empty result is ambiguous: say whether the master exists at all.
        m = q(conn, "SELECT name FROM tally_ledger WHERE name ILIKE %s LIMIT 5",
              (f"%{term}%",))
        if m:
            print("  But these ledger masters exist with NO transactions:")
            for r in m:
                print(f"    - {r[0]}")
        return
    print(f"Ledgers matching '{term}': {len(names)}\n")
    for (n,) in names:
        rows = q(conn, """
            SELECT v.fin_year, COUNT(*),
                   SUM(CASE WHEN e.is_debit THEN e.amount ELSE 0 END),
                   SUM(CASE WHEN NOT e.is_debit THEN e.amount ELSE 0 END)
            FROM tally_entry e JOIN tally_voucher v ON v.id=e.voucher_id
            WHERE e.ledger_name=%s GROUP BY v.fin_year ORDER BY 1""", (n,))
        tot_d = sum(r[2] or 0 for r in rows)
        tot_c = sum(r[3] or 0 for r in rows)
        print(f"  {n}")
        print(table([(r[0], r[1], rupees(r[2]), rupees(r[3])) for r in rows]
                    + [("TOTAL", sum(r[1] for r in rows),
                        rupees(tot_d), rupees(tot_c))],
                    ["FY", "entries", "debit", "credit"]))
        print()


def cmd_vendor(conn, args):
    """Everything booked against one party.

    Matches on a WORD boundary, not a bare substring. Searching 'ARTH' as a
    substring also returns Kritarth, Parth Cooling and Siddharth Enterprises —
    three unrelated vendors silently folded into one vendor's history, which is
    exactly the kind of quiet wrongness that makes a total untrustworthy.
    """
    term = args[0]
    pattern = r"\m" + re.escape(term).replace("\\", "") + r"\M"
    names = q(conn, """
        SELECT DISTINCT e.ledger_name FROM tally_entry e
        WHERE e.ledger_name ~* %s ORDER BY 1""", (pattern,))
    if not names:
        print(f"  No ledger matches '{term}' as a whole word.")
        near = q(conn, """SELECT DISTINCT ledger_name FROM tally_entry
                          WHERE ledger_name ILIKE %s LIMIT 8""", (f"%{term}%",))
        if near:
            print("  Did you mean one of these (substring matches)?")
            for (n,) in near:
                print(f"    - {n}")
        return
    print(f"Ledgers matched: {', '.join(n for (n,) in names)}\n")
    rows = q(conn, """
        SELECT v.voucher_date, v.fin_year, v.voucher_type, v.voucher_number,
               e.ledger_name,
               CASE WHEN e.is_debit THEN e.amount ELSE -e.amount END,
               COALESCE(v.narration,'')
        FROM tally_entry e JOIN tally_voucher v ON v.id=e.voucher_id
        WHERE e.ledger_name ~* %s
        ORDER BY v.voucher_date""", (pattern,))
    print(f"{len(rows)} entries\n")
    print(table([(str(r[0]), r[1], r[2], r[3], r[4][:28],
                  rupees(r[5]), r[6][:42]) for r in rows],
                ["date", "FY", "type", "no", "ledger", "amount", "narration"]))

    print("\n  Year by year — invoices booked (credit) vs paid (debit):")
    summary = q(conn, """
        SELECT v.fin_year,
               SUM(CASE WHEN e.is_debit THEN e.amount ELSE 0 END),
               SUM(CASE WHEN NOT e.is_debit THEN e.amount ELSE 0 END)
        FROM tally_entry e JOIN tally_voucher v ON v.id=e.voucher_id
        WHERE e.ledger_name ~* %s GROUP BY v.fin_year ORDER BY 1""", (pattern,))
    print(table([(r[0], rupees(r[2]), rupees(r[1]), rupees((r[2] or 0)-(r[1] or 0)))
                 for r in summary]
                + [("TOTAL", rupees(sum(r[2] or 0 for r in summary)),
                    rupees(sum(r[1] or 0 for r in summary)),
                    rupees(sum((r[2] or 0)-(r[1] or 0) for r in summary)))],
                ["FY", "billed", "paid", "outstanding"]))


def cmd_tds(conn, _):
    print("TDS LEDGERS ACROSS ALL YEARS\n")
    rows = q(conn, """
        SELECT e.ledger_name, v.fin_year, COUNT(*),
               SUM(CASE WHEN e.is_debit THEN e.amount ELSE 0 END),
               SUM(CASE WHEN NOT e.is_debit THEN e.amount ELSE 0 END)
        FROM tally_entry e JOIN tally_voucher v ON v.id=e.voucher_id
        WHERE e.ledger_name ILIKE %s OR e.ledger_name ILIKE %s
           OR e.ledger_name ILIKE %s
        GROUP BY e.ledger_name, v.fin_year
        ORDER BY e.ledger_name, v.fin_year""",
             ("%TDS%", "%194%", "%Tax Deducted%"))
    if not rows:
        print("  No ledger with 'TDS' in its name carries any entry.")
        return
    print(table([(r[0][:44], r[1], r[2], rupees(r[3]), rupees(r[4]))
                 for r in rows],
                ["ledger", "FY", "entries", "debit", "credit"]))


def cmd_search(conn, args):
    term = args[0]
    rows = q(conn, """
        SELECT v.voucher_date, v.fin_year, v.voucher_type,
               v.voucher_number, COALESCE(v.narration,'')
        FROM tally_voucher v WHERE v.narration ILIKE %s
        ORDER BY v.voucher_date LIMIT 120""", (f"%{term}%",))
    print(f"Vouchers whose narration mentions '{term}': {len(rows)}"
          f"{' (capped at 120)' if len(rows)==120 else ''}\n")
    print(table([(str(r[0]), r[1], r[2], r[3], r[4][:70]) for r in rows],
                ["date", "FY", "type", "no", "narration"]))


def cmd_sql(conn, args):
    sql = args[0]
    if not re.match(r"^\s*(SELECT|WITH)\b", sql, re.I):
        sys.exit("read-only: only SELECT/WITH allowed")
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        rows = cur.fetchall()
    print(table([tuple(rupees(v) if isinstance(v, float) else v for v in r)
                 for r in rows], cols))
    print(f"\n  {len(rows)} rows")


COMMANDS = {"overview": cmd_overview, "year": cmd_year, "ledger": cmd_ledger,
            "vendor": cmd_vendor, "tds": cmd_tds, "search": cmd_search,
            "sql": cmd_sql}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(textwrap.dedent(__doc__))
        return 1
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd in ("year", "ledger", "vendor", "search", "sql") and not args:
        sys.exit(f"{cmd} needs an argument")
    with psycopg.connect(DSN) as conn:
        COMMANDS[cmd](conn, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
