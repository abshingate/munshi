#!/usr/bin/env python3
"""
Advisor cross-check — make disagreements visible, not resolved.

This does NOT decide who is right. A professional adviser knows things the
rule set does not: a client's history, an assessing officer's view, a
judgement the statute does not spell out. Overriding them automatically would
be worse than the problem.

What it does is refuse to let a disagreement pass silently. When recorded
advice conflicts with an encoded rule, both positions are shown with their
sources, and the operator decides — knowing a conflict exists.

The motivating case, from the record:

    2026-01-29 09:58  the adviser's own tax team:
        "TDS payable of Rs. 12,500 along with interest of Rs. 750.
         Request you to kindly pay this amount."
    2026-01-29 11:11  the same team, 73 minutes later:
        "As discussed over the phone, please ignore the previous email.
         Tax is not deducted since the company already has significant
         accumulated losses."

The second position is wrong: losses affect the s.40(a)(ia) disallowance, not
the deductor's liability under s.201. It was followed because nobody had a
mechanism to notice the conflict. That mechanism is this file.

A second reason to record advice: when it turns out to be wrong, the record
of having relied on it in good faith matters — for penalty proceedings and
for deciding whether to keep the adviser.

Usage
-----
    python3 crosscheck.py --list
    python3 crosscheck.py --check
    python3 crosscheck.py --add           (interactive)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tds_engine import TdsEngine  # noqa: E402

ADVICE_FILE = Path(__file__).parent / "advice.json"


def load_advice() -> dict:
    if not ADVICE_FILE.exists():
        return {"description": "Professional advice received, and whether it "
                               "agrees with the encoded rules.",
                "advice": []}
    return json.loads(ADVICE_FILE.read_text(encoding="utf-8"))


def save_advice(data: dict):
    ADVICE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")


# ---------------------------------------------------------------------------
# Cross-checking
# ---------------------------------------------------------------------------

def check_one(item: dict, engine: TdsEngine) -> dict:
    """Compare one piece of advice against the rules.

    Returns a verdict, never an instruction. 'conflict' means look at this,
    not 'the adviser is wrong'.
    """
    result = {
        "id": item["id"],
        "subject": item.get("subject", ""),
        "advisor": item.get("advisor", ""),
        "date": item.get("date", ""),
        "advice": item.get("advice", ""),
        "verdict": "not-checkable",
        "rule_says": None,
        "note": "",
    }

    claim = item.get("claim")
    if not claim:
        result["note"] = ("no machine-checkable claim recorded — kept for the "
                          "audit trail only")
        return result

    kind = claim.get("kind")

    if kind == "tds-applies":
        rule_id = claim["rule_id"]
        amount = float(claim["amount"])
        on = date.fromisoformat(claim["on_date"])
        prior = float(claim.get("prior_year_total", 0))
        try:
            a = engine.assess(rule_id, amount, on, prior_year_total=prior)
        except (KeyError, ValueError) as e:
            result["note"] = f"could not evaluate: {e}"
            return result

        advised = bool(claim["advised_applies"])
        result["rule_says"] = {
            "applies": a.applies, "tds": a.tds,
            "explanation": a.explanation, "authority": a.authority,
        }
        if a.applies == advised:
            result["verdict"] = "agrees"
            result["note"] = "advice and the encoded rule reach the same conclusion"
        else:
            result["verdict"] = "conflict"
            result["note"] = (
                f"the adviser says TDS {'applies' if advised else 'does not apply'}; "
                f"the rule says it {'applies' if a.applies else 'does not apply'}"
            )
            if claim.get("advised_amount") is not None:
                result["note"] += (f". Advised amount {float(claim['advised_amount']):,.2f}, "
                                   f"rule computes {a.tds:,.2f}")

    elif kind == "amount":
        expected = float(claim["rule_amount"])
        advised = float(claim["advised_amount"])
        result["rule_says"] = {"amount": expected,
                               "authority": claim.get("authority", "")}
        if abs(expected - advised) < 1.0:
            result["verdict"] = "agrees"
        else:
            result["verdict"] = "conflict"
            result["note"] = (f"adviser says {advised:,.2f}, rule computes "
                              f"{expected:,.2f} (difference {abs(expected-advised):,.2f})")

    elif kind == "assertion":
        # A stated legal proposition checked against a recorded counter-rule.
        result["rule_says"] = {"position": claim.get("rule_position", ""),
                               "authority": claim.get("authority", "")}
        result["verdict"] = "conflict" if claim.get("contradicts_rule") else "agrees"
        result["note"] = claim.get("why", "")

    return result


def run_checks(engine: TdsEngine) -> list[dict]:
    data = load_advice()
    return [check_one(a, engine) for a in data["advice"]]


def print_results(results: list[dict], only_conflicts: bool = False):
    conflicts = [r for r in results if r["verdict"] == "conflict"]
    agrees = [r for r in results if r["verdict"] == "agrees"]
    unchecked = [r for r in results if r["verdict"] == "not-checkable"]

    if conflicts:
        print("\nCONFLICTS — advice disagrees with the encoded rules")
        print("=" * 72)
        for r in conflicts:
            print(f"\n  [{r['id']}] {r['date']}  {r['advisor']}")
            print(f"  Subject : {r['subject']}")
            print(f"  Advised : {r['advice']}")
            if r["rule_says"]:
                rs = r["rule_says"]
                if "explanation" in rs:
                    print(f"  Rule    : {rs['explanation']}")
                elif "position" in rs:
                    print(f"  Rule    : {rs['position']}")
                elif "amount" in rs:
                    print(f"  Rule    : {rs['amount']:,.2f}")
                if rs.get("authority"):
                    print(f"  Authority: {rs['authority']}")
            print(f"  -> {r['note']}")
        print("\n" + "-" * 72)
        print("  These are NOT rulings. An adviser may know something the rule")
        print("  set does not. But the disagreement should be a decision you")
        print("  make knowingly, in writing, rather than one that passes")
        print("  unnoticed.")

    if not only_conflicts:
        if agrees:
            print(f"\nAGREES ({len(agrees)})")
            for r in agrees:
                print(f"  [{r['id']}] {r['subject'][:60]}")
        if unchecked:
            print(f"\nRECORDED, NOT MACHINE-CHECKABLE ({len(unchecked)})")
            for r in unchecked:
                print(f"  [{r['id']}] {r['subject'][:60]}")

    if not conflicts:
        print("\nNo conflicts between recorded advice and the encoded rules.")
    print()
    return len(conflicts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Cross-check professional advice")
    ap.add_argument("--list", action="store_true", help="show all recorded advice")
    ap.add_argument("--check", action="store_true", help="conflicts only")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    engine = TdsEngine()
    results = run_checks(engine)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
        return 0

    n = print_results(results, only_conflicts=args.check)
    # Non-zero exit when a conflict stands, so this can gate a workflow.
    return 1 if n else 0


if __name__ == "__main__":
    raise SystemExit(main())
