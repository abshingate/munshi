#!/usr/bin/env python3
"""
Tests for advisor cross-check.

The behaviour under test is unusual: this component must NOT decide who is
right. It must detect a disagreement, present both positions with sources,
and stop. Tests therefore assert as much about restraint as about detection.

    python3 test_crosscheck.py
"""

import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import crosscheck  # noqa: E402
from tds_engine import TdsEngine  # noqa: E402

HERE = Path(__file__).parent


class TestConflictDetection(unittest.TestCase):
    def setUp(self):
        self.eng = TdsEngine()

    def test_agreeing_advice_is_not_flagged(self):
        item = {
            "id": "T1", "subject": "t", "advisor": "x", "date": "2026-04-01",
            "advice": "TDS of 12,500 applies",
            "claim": {"kind": "tds-applies", "rule_id": "tds-professional-fees",
                      "amount": 125000, "on_date": "2026-04-01",
                      "advised_applies": True, "advised_amount": 12500},
        }
        self.assertEqual(crosscheck.check_one(item, self.eng)["verdict"], "agrees")

    def test_disagreeing_advice_is_flagged(self):
        item = {
            "id": "T2", "subject": "t", "advisor": "x", "date": "2026-04-01",
            "advice": "no TDS needed",
            "claim": {"kind": "tds-applies", "rule_id": "tds-professional-fees",
                      "amount": 125000, "on_date": "2026-04-01",
                      "advised_applies": False},
        }
        r = crosscheck.check_one(item, self.eng)
        self.assertEqual(r["verdict"], "conflict")
        # The rule's own reasoning must be shown, not merely a verdict.
        self.assertIn("explanation", r["rule_says"])
        self.assertTrue(r["rule_says"]["authority"])

    def test_advice_without_a_claim_is_kept_not_judged(self):
        """Advice that cannot be machine-checked must be recorded, never
        guessed at."""
        item = {"id": "T3", "subject": "t", "advisor": "x",
                "date": "2026-04-01", "advice": "something qualitative",
                "claim": None}
        r = crosscheck.check_one(item, self.eng)
        self.assertEqual(r["verdict"], "not-checkable")
        self.assertIn("audit trail", r["note"])

    def test_amount_disagreement_reports_the_difference(self):
        item = {"id": "T4", "subject": "t", "advisor": "x", "date": "2026-04-01",
                "advice": "pay 10,000",
                "claim": {"kind": "amount", "rule_amount": 12500,
                          "advised_amount": 10000, "authority": "s.194J"}}
        r = crosscheck.check_one(item, self.eng)
        self.assertEqual(r["verdict"], "conflict")
        self.assertIn("2,500", r["note"])

    def test_unevaluable_claim_does_not_crash(self):
        item = {"id": "T5", "subject": "t", "advisor": "x", "date": "2026-04-01",
                "advice": "x",
                "claim": {"kind": "tds-applies", "rule_id": "does-not-exist",
                          "amount": 1000, "on_date": "2026-04-01",
                          "advised_applies": True}}
        r = crosscheck.check_one(item, self.eng)
        self.assertEqual(r["verdict"], "not-checkable")
        self.assertIn("could not evaluate", r["note"])


class TestRestraint(unittest.TestCase):
    """The component must not pretend to authority it does not have."""

    def test_conflict_output_disclaims_being_a_ruling(self):
        import io
        import contextlib
        eng = TdsEngine()
        results = crosscheck.run_checks(eng)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            crosscheck.print_results(results)
        out = buf.getvalue()
        if any(r["verdict"] == "conflict" for r in results):
            self.assertIn("NOT rulings", out)
            self.assertIn("adviser may know something", out)


class TestAdviceRegister(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((HERE / "advice.json").read_text(encoding="utf-8"))

    def test_register_parses(self):
        self.assertIn("advice", self.data)

    def test_ids_unique(self):
        ids = [a["id"] for a in self.data["advice"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_entry_records_a_source(self):
        """Advice without a source cannot be relied on later, which is half
        the reason for recording it."""
        for a in self.data["advice"]:
            self.assertTrue(a.get("source", "").strip(),
                            f"{a['id']} has no source")

    def test_every_entry_quotes_the_advice(self):
        for a in self.data["advice"]:
            self.assertTrue(a.get("advice", "").strip(),
                            f"{a['id']} does not record what was advised")

    def test_contradicting_claims_cite_authority(self):
        for a in self.data["advice"]:
            c = a.get("claim") or {}
            if c.get("contradicts_rule"):
                self.assertTrue(c.get("authority", "").strip(),
                                f"{a['id']} claims a conflict without citing authority")

    def test_the_real_case_is_detected(self):
        """A002 — the withdrawn position — must register as a conflict."""
        eng = TdsEngine()
        results = {r["id"]: r for r in crosscheck.run_checks(eng)}
        self.assertEqual(results["A002"]["verdict"], "conflict")
        self.assertEqual(results["A001"]["verdict"], "agrees")


if __name__ == "__main__":
    unittest.main(verbosity=2)
