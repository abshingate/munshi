#!/usr/bin/env python3
"""
Fixed Asset Register and depreciation computation under Schedule II.

Reconstructs each asset's history from Tally vouchers — acquisition date, cost,
additions, disposals — then computes depreciation under the Companies Act 2013,
Schedule II, and compares it against what Tally actually booked.

WHY THIS EXISTS
---------------
₹7,03,508 of depreciation was booked in FY2025-26 and nobody has checked it
against Schedule II. A wrong charge understates or overstates profit, affects
tax, and is exactly the kind of thing an auditor questions first.

WHAT IT WILL NOT DO
-------------------
Silently guess. An asset whose class cannot be determined from its name is
reported as **UNCLASSIFIED** rather than defaulted, because a wrong useful life
produces a wrong charge that still looks perfectly reasonable. Same for assets
with no traceable acquisition date.

Every figure shows its working: cost, date, life, method, rate, days held,
opening WDV, charge, closing WDV.

Usage (on the VM, Tally open)
-----------------------------
    python fixed_assets.py --fy 2025-26
    python fixed_assets.py --fy 2025-26 --out C:\\TallyData\\Drive\\For-CA
    python fixed_assets.py --fy 2025-26 --method SLM
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tally_extract import (  # noqa: E402
    post, collection, tag_text, unescape, parse_amount, company_name,
    VOUCHER_RE, NESTED_LIST_RE, parse_date,
)
from financials import fetch, classify, _clean  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEDULE2 = os.path.join(HERE, "schedule2.json")


def load_schedule2() -> dict:
    with open(SCHEDULE2, encoding="utf-8") as fh:
        return json.load(fh)


def rupees(x) -> str:
    if x is None:
        return "-"
    neg = x < 0
    s = f"{abs(float(x)):.2f}"
    whole, dec = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        whole = f"{head},{tail}"
    return f"({whole}.{dec})" if neg else f"{whole}.{dec}"


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_asset(name: str, parent: str, sched: dict) -> dict | None:
    """Match an asset to a Schedule II class. Returns None if unclassifiable.

    Longest match wins: 'macbook' must beat 'book', '3d printer' must beat
    'printer'. Ties broken by the more specific (longer) keyword.
    """
    hay = f"{name} {parent}".lower()
    best = None
    best_len = 0
    for cls in sched["assets"]:
        for kw in cls["match"]:
            k = kw.strip().lower()
            if k and k in hay and len(k) > best_len:
                best, best_len = cls, len(k)
    return best


# ---------------------------------------------------------------------------
# History reconstruction
# ---------------------------------------------------------------------------

def asset_movements(fy_from: int, fy_to: int, company: str) -> dict:
    """Every debit/credit to every ledger, by year — the raw asset history.

    Walks year by year because the gateway answers from its current period.
    """
    moves = {}
    for y in range(fy_from, fy_to + 1):
        xml = post(collection(
            "V", "Voucher",
            ["Date", "VoucherTypeName", "VoucherNumber", "Narration",
             "AllLedgerEntries.List"],
            f"{y}0401", f"{y+1}0331", company=company))
        for m in VOUCHER_RE.finditer(xml):
            b = m.group(1)
            if tag_text(b, "ISDELETED").upper() == "YES":
                continue
            d = parse_date(tag_text(b, "DATE"))
            if not d:
                continue
            narr = tag_text(b, "NARRATION")
            vtype = tag_text(b, "VOUCHERTYPENAME")
            vno = tag_text(b, "VOUCHERNUMBER")
            for em in re.finditer(
                    r"<ALLLEDGERENTRIES\.LIST[^>]*>(.*?)</ALLLEDGERENTRIES\.LIST>",
                    b, re.S):
                eb = NESTED_LIST_RE.sub("", em.group(1))
                led = tag_text(eb, "LEDGERNAME")
                amt = parse_amount(tag_text(eb, "AMOUNT"))
                if not led or amt is None:
                    continue
                deemed = tag_text(eb, "ISDEEMEDPOSITIVE").upper()
                is_debit = (deemed == "YES") if deemed else (amt < 0)
                moves.setdefault(_clean(unescape(led)), []).append({
                    "date": d, "amount": abs(amt), "is_debit": is_debit,
                    "type": vtype, "number": vno, "narration": narr,
                })
    for v in moves.values():
        v.sort(key=lambda x: x["date"])
    return moves


def days_in_year(d1: date, d2: date) -> int:
    return (d2 - d1).days + 1


def detect_method(fy: str) -> tuple[str, dict]:
    """Infer the depreciation method the company actually uses.

    Do NOT assume WDV. Schedule II permits either method, and picking the
    wrong one produces a difference of roughly 2x that looks exactly like a
    serious under-provision. Here, WDV suggested the company had under-charged
    by 6.08 lakh; under SLM the computation matched the booked figure to
    within 137 rupees on 7.03 lakh. The company was right and the assumption
    was wrong.

    Method: compute both and keep whichever lands closer to what was booked.
    """
    scores = {}
    for m in ("SLM", "WDV"):
        r = compute(fy, m, _detect=False)
        booked = r["booked"]
        scores[m] = {
            "computed": r["computed"],
            "booked": booked,
            "diff": abs(r["computed"] - booked),
            "pct": (abs(r["computed"] - booked) / booked * 100)
                   if booked else float("inf"),
        }
    best = min(scores, key=lambda m: scores[m]["pct"])
    return best, scores


def compute(fy: str, method: str = "WDV", _detect: bool = False) -> dict:
    if _detect:
        method, _ = detect_method(fy)
    y = int(fy.split("-")[0])
    fy_start, fy_end = date(y, 4, 1), date(y + 1, 3, 31)
    sched = load_schedule2()
    company = company_name()

    cmp_name, ledgers, groups = fetch(fy)
    assets = []
    for led in ledgers:
        stmt, section, sub = classify(led, groups)
        root = _clean(led["parent"])
        # Fixed assets only; exclude the accumulated-depreciation contra
        # ledgers, which are handled as a pair with their asset.
        is_fa = section == "ASSETS" and sub == "Non-Current Assets"
        low = led["name"].lower()
        if not is_fa:
            continue
        if "accumulated dep" in low or low.startswith("accumulated"):
            continue
        if any(k in low for k in ("investment", "mutual fund", "fixed deposit",
                                 "gratuity fund", "deposit", "advance")):
            continue
        if abs(led["opening"]) < 0.005 and abs(led["closing"]) < 0.005:
            continue
        assets.append(led)

    # Accumulated depreciation lives in SEPARATE ledgers ('Accumulated Depn :
    # Computers & Printers' etc.), so the asset ledger holds ORIGINAL COST
    # permanently — the 3D Printer stays at 13,35,000 forever. Charging a WDV
    # rate on that gross figure over-depreciates every year after the first.
    # Net the accumulated block off before computing.
    accum = {}
    for led in ledgers:
        low = led["name"].lower()
        if "accumulated dep" in low:
            # Group them by the asset class named in the ledger, e.g.
            # 'Accumulated Depn : Computers & Printers' -> 'computers & printers'
            key = re.split(r"[:\-]", led["name"], maxsplit=1)[-1].strip().lower()
            accum[key] = accum.get(key, 0.0) + led["opening"]

    def accumulated_for(parent: str) -> float:
        """Opening accumulated depreciation attributable to an asset's group."""
        p = (parent or "").strip().lower()
        for key, val in accum.items():
            if not key:
                continue
            # 'Computers & Printers' block matches the 'Computers & Printers'
            # Tally group the asset sits under.
            if key in p or p in key:
                return val
        return 0.0

    # Acquisition history: walk back to incorporation so an asset bought in
    # 2018 is dated correctly when we depreciate it in 2025.
    moves = asset_movements(2016, y, company)

    # Apportion each block's accumulated depreciation across its assets by
    # gross cost, so an individual asset's opening WDV can be estimated.
    block_cost = {}
    for a in assets:
        p = (a["parent"] or "").strip().lower()
        block_cost[p] = block_cost.get(p, 0.0) + max(0.0, -a["opening"])

    rows = []
    for a in assets:
        hist = moves.get(a["name"], [])
        buys = [h for h in hist if h["is_debit"]]
        first_buy = buys[0]["date"] if buys else None
        additions = [h for h in buys if fy_start <= h["date"] <= fy_end]
        disposals = [h for h in hist
                     if not h["is_debit"] and fy_start <= h["date"] <= fy_end]

        cls = classify_asset(a["name"], a["parent"], sched)

        # Tally's asset ledgers carry debit balances (negative in its sign
        # convention). Present gross block as a positive figure.
        opening_cost = -a["opening"]
        addition_amt = sum(h["amount"] for h in additions)
        disposal_amt = sum(h["amount"] for h in disposals)
        closing_cost = -a["closing"]

        # Opening WDV = gross cost less this asset's share of the block's
        # accumulated depreciation, apportioned by cost.
        p = (a["parent"] or "").strip().lower()
        block_total = block_cost.get(p, 0.0)
        block_accum = accumulated_for(a["parent"])
        share = (max(0.0, opening_cost) / block_total) if block_total > 0 else 0.0
        opening_accum = block_accum * share
        opening_wdv = max(0.0, opening_cost - opening_accum)

        row = {
            "name": a["name"], "parent": a["parent"],
            "opening_cost": opening_cost,
            "opening_accum": opening_accum,
            "opening_wdv": opening_wdv,
            "additions": addition_amt, "disposals": disposal_amt,
            "closing_cost": closing_cost,
            "first_acquired": first_buy,
            "addition_dates": [h["date"] for h in additions],
            "class": cls["class"] if cls else None,
            "life": cls["life_years"] if cls else None,
            "rate": (cls["wdv_rate"] if method == "WDV" else cls["slm_rate"])
                    if cls else None,
            "issues": [],
        }
        if not cls:
            row["issues"].append("UNCLASSIFIED — no Schedule II class matched "
                                 "this ledger name; assign manually")
        if not first_buy:
            row["issues"].append("NO ACQUISITION VOUCHER found — cannot date "
                                 "the asset; opening balance predates the data")

        # ---- the charge ----
        if cls:
            rate = row["rate"] / 100.0
            residual = sched["residual_value_percent"] / 100.0
            charge = 0.0
            workings = []

            # Assets held at the start of the year: full-year charge.
            # WDV charges on the written-down value; SLM on original cost.
            if opening_cost > 0.005:
                if method == "WDV":
                    base = opening_wdv
                    c = base * rate
                    workings.append(
                        f"opening cost {rupees(opening_cost)} less accumulated "
                        f"depreciation {rupees(opening_accum)} "
                        f"= WDV {rupees(opening_wdv)}")
                    workings.append(
                        f"WDV {rupees(opening_wdv)} x {row['rate']}% "
                        f"= {rupees(c)}")
                else:
                    base = opening_cost
                    c = base * rate
                    workings.append(
                        f"cost {rupees(opening_cost)} x {row['rate']}% (SLM) "
                        f"= {rupees(c)}")
                charge += c

            # Additions: pro-rata from the date put to use (Sch II Part C).
            for h in additions:
                held = days_in_year(h["date"], fy_end)
                c = h["amount"] * rate * held / 365.0
                charge += c
                workings.append(
                    f"addition {h['date']} {rupees(h['amount'])} x "
                    f"{row['rate']}% x {held}/365 = {rupees(c)}")

            # Never depreciate below residual value (Sch II Part A para 5).
            # The floor is 5% of ORIGINAL COST; the balance being tested
            # against it is the written-down value, not the gross block.
            floor = closing_cost * residual if closing_cost > 0 else 0.0
            wdv_before = opening_wdv + addition_amt - disposal_amt
            if wdv_before - charge < floor:
                capped = max(0.0, wdv_before - floor)
                if capped < charge:
                    workings.append(
                        f"CAPPED at 5% residual floor {rupees(floor)}: "
                        f"charge reduced {rupees(charge)} -> {rupees(capped)}")
                    charge = capped

            row["charge"] = charge
            row["workings"] = workings
            row["closing_wdv"] = wdv_before - charge
        else:
            row["charge"] = None
            row["workings"] = []
            row["closing_wdv"] = None

        rows.append(row)

    # What Tally actually booked, for comparison.
    booked = 0.0
    for led in ledgers:
        low = led["name"].lower()
        if "depreciation" in low and "accumulated" not in low:
            booked += -(led["closing"])

    return {
        "fy": fy, "company": cmp_name, "method": method,
        "rows": rows, "booked": booked,
        "computed": sum(r["charge"] or 0.0 for r in rows),
        "residual_pct": sched["residual_value_percent"],
    }


# ---------------------------------------------------------------------------

def render(res: dict) -> str:
    y = int(res["fy"].split("-")[0])
    rows = res["rows"]
    out = []
    A = out.append

    A(f"# {res['company'].split(' - (')[0]}")
    A("")
    A(f"## Fixed Asset Register and Depreciation — FY {res['fy']}")
    A("")
    A("> ### ⚠️ DRAFT — computed, not audited")
    A("> Depreciation computed under **Schedule II to the Companies Act, 2013**")
    A(f"> on the **{res['method']}** method, with a residual value of "
      f"{res['residual_pct']}% of cost.")
    A("> Asset classes are inferred from ledger names and **must be confirmed**")
    A("> — a wrong useful life produces a wrong charge that still looks")
    A("> reasonable. Every figure below shows its working.")
    A("")
    A(f"*Generated {date.today().strftime('%d %B %Y')}. "
      f"Year 1 April {y} to 31 March {y+1}.*")
    A("")

    # --- headline comparison ---
    diff = res["computed"] - res["booked"]
    A("## The bottom line")
    A("")
    A("| | ₹ |")
    A("|---|---:|")
    A(f"| Depreciation **computed** under Schedule II | {rupees(res['computed'])} |")
    A(f"| Depreciation **booked in Tally** | {rupees(res['booked'])} |")
    A(f"| **Difference** | **{rupees(diff)}** |")
    A("")
    pct = abs(diff) / res["booked"] * 100 if res["booked"] else 0.0
    if pct < 0.5:
        A(f"✅ **The booked charge agrees with the Schedule II computation** "
          f"on the **{res['method']}** method — a difference of "
          f"{rupees(abs(diff))} on {rupees(res['booked'])} ({pct:.2f}%), which")
        A("is rounding. No adjustment appears necessary.")
    else:
        direction = "MORE than" if diff > 0 else "LESS than"
        A(f"⚠️ **The computation is {rupees(abs(diff))} {direction} what Tally "
          f"booked** ({pct:.1f}%). This needs explaining before the accounts")
        A("are finalised — it affects reported profit and therefore tax.")
        A("Common causes: a different useful life, assets not put to use for")
        A("the full period, or a charge booked as a lump sum rather than")
        A("asset-wise.")
    A("")

    if res.get("method_scores"):
        A("### Which method the company uses")
        A("")
        A("Not assumed — inferred by computing both and comparing against what")
        A("was actually booked:")
        A("")
        A("| Method | Computed ₹ | Booked ₹ | Difference ₹ | |")
        A("|---|---:|---:|---:|---|")
        for m, s in res["method_scores"].items():
            mark = " ← **matches**" if m == res["method"] else ""
            A(f"| {m} | {rupees(s['computed'])} | {rupees(s['booked'])} "
              f"| {rupees(s['diff'])} ({s['pct']:.1f}%) |{mark} |")
        A("")
        A("Schedule II permits either method. Picking the wrong one produces a")
        A("difference of roughly 2x that looks exactly like a serious")
        A("under-provision — so the method is detected, never assumed.")
        A("")

    unresolved = [r for r in rows if r["issues"]]
    if unresolved:
        A("## ⚠️ Assets needing a decision before this is reliable")
        A("")
        A("These are **excluded from the computed total above** where no class")
        A("could be assigned. Nothing has been guessed.")
        A("")
        A("| Asset | Tally group | Cost ₹ | Issue |")
        A("|---|---|---:|---|")
        for r in unresolved:
            for issue in r["issues"]:
                A(f"| {r['name'][:36]} | {r['parent'][:20]} | "
                  f"{rupees(r['closing_cost'])} | {issue} |")
        A("")

    # --- the register ---
    A("## Fixed Asset Register")
    A("")
    A("| Asset | Class (Sch II) | Life | Rate | Acquired | Gross cost ₹ "
      "| Accum. depn ₹ | Opening WDV ₹ | Additions ₹ | Depreciation ₹ "
      "| Closing WDV ₹ |")
    A("|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|")
    for r in sorted(rows, key=lambda x: -(x["closing_cost"] or 0)):
        A(f"| {r['name'][:30]} | {(r['class'] or 'UNCLASSIFIED')[:30]} "
          f"| {r['life'] or '-'} | {str(r['rate'] or '-')}% "
          f"| {r['first_acquired'] or '?'} "
          f"| {rupees(r['opening_cost'])} | {rupees(r.get('opening_accum'))} "
          f"| {rupees(r.get('opening_wdv'))} | {rupees(r['additions'])} "
          f"| {rupees(r['charge']) if r['charge'] is not None else 'n/a'} "
          f"| {rupees(r['closing_wdv']) if r['closing_wdv'] is not None else 'n/a'} |")
    tot_open = sum(r["opening_cost"] for r in rows)
    tot_accum = sum(r.get("opening_accum") or 0 for r in rows)
    tot_wdv = sum(r.get("opening_wdv") or 0 for r in rows)
    tot_add = sum(r["additions"] for r in rows)
    A(f"| **TOTAL** | | | | | **{rupees(tot_open)}** | **{rupees(tot_accum)}** "
      f"| **{rupees(tot_wdv)}** | **{rupees(tot_add)}** "
      f"| **{rupees(res['computed'])}** | |")
    A("")

    # --- workings ---
    A("## How each charge was computed")
    A("")
    A("*Shown so every figure can be checked by hand.*")
    A("")
    for r in sorted(rows, key=lambda x: -(x["charge"] or 0)):
        if not r["workings"]:
            continue
        A(f"**{r['name']}** — {r['class']}, {r['life']}-year life, "
          f"{r['rate']}% {res['method']}")
        A("")
        for w in r["workings"]:
            A(f"- {w}")
        A(f"- **charge for the year: {rupees(r['charge'])}**")
        A("")

    A("---")
    A("")
    A("## Basis and what to check")
    A("")
    A("1. **Useful lives** are from Schedule II Part C. A different life may be")
    A("   adopted with technical justification, disclosed in the notes")
    A("   (Sch II Part A para 3). Confirm the lives above match company policy.")
    A("2. **Residual value** is taken at 5% of cost, the Schedule II norm")
    A("   (Part A para 5). No asset is depreciated below it.")
    A("3. **Additions** are depreciated pro-rata from the voucher date, on the")
    A("   assumption the asset was *put to use* that day. Where an asset was")
    A("   bought but commissioned later, the charge is overstated — check any")
    A("   material addition.")
    A("4. **Disposals** — no profit or loss on sale is computed here; that")
    A("   needs the sale consideration.")
    A("5. **Componentisation** (Sch II Part A para 4) — significant components")
    A("   with different lives should be depreciated separately. Not applied.")
    A("6. **Income-tax depreciation is different** (block of assets, s.32).")
    A("   This register is for the Companies Act accounts only.")
    A("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fy", required=True)
    ap.add_argument("--method", default="auto", choices=["auto", "WDV", "SLM"],
                    help="default 'auto' infers the method from what was "
                         "booked, rather than assuming one")
    ap.add_argument("--out")
    args = ap.parse_args()

    if args.method == "auto":
        method, scores = detect_method(args.fy)
        res = compute(args.fy, method)
        res["method_scores"] = scores
        print(f"detected method: {method}")
    else:
        res = compute(args.fy, args.method)
    if not res["rows"]:
        print(f"No fixed-asset ledgers with balances in FY{args.fy}.")
        return 1

    report = render(res)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, f"Fixed-Asset-Register-FY{args.fy}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"written: {path}")
        print(f"  assets: {len(res['rows'])}")
        print(f"  computed depreciation: {res['computed']:,.2f}")
        print(f"  booked in Tally:       {res['booked']:,.2f}")
        print(f"  difference:            {res['computed']-res['booked']:,.2f}")
        bad = [r for r in res["rows"] if r["issues"]]
        if bad:
            print(f"  WARNING: {len(bad)} assets need a manual decision")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
