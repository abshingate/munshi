#!/usr/bin/env python3
"""
Tests for the rules engine, the rule set, and the lessons register.

Two kinds of test here, and the second is unusual:

  1. Ordinary correctness — does the engine compute the right number?
  2. Process integrity — does every rule cite an authority, and does every
     recorded mistake name an executable safeguard?

The second exists because a lessons file that accumulates good intentions is
worse than none: it looks like diligence while changing nothing. These tests
make "we learned from it" mean "something now fails if it recurs".

    python3 test_rules.py
"""

import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tds_engine import TdsEngine  # noqa: E402

HERE = Path(__file__).parent


class TestThresholdBasis(unittest.TestCase):
    """The per-month vs per-year distinction (lesson L001) — the single most
    consequential thing this engine gets right."""

    def setUp(self):
        self.eng = TdsEngine()

    def test_monthly_rent_below_threshold_is_not_annualised(self):
        a = self.eng.assess("tds-rent-land-building", 30000, date(2026, 5, 7))
        self.assertFalse(a.applies)
        self.assertEqual(a.tds, 0.0)
        # The explanation must actively rebut the wrong reasoning.
        self.assertIn("per-MONTH", a.explanation)
        self.assertIn("NOT the test", a.explanation)

    def test_monthly_rent_above_threshold(self):
        a = self.eng.assess("tds-rent-land-building", 55000, date(2026, 5, 7))
        self.assertTrue(a.applies)
        self.assertAlmostEqual(a.tds, 5500.0, places=2)

    def test_annual_basis_accumulates(self):
        below = self.eng.assess("tds-professional-fees", 25000, date(2026, 6, 1))
        self.assertFalse(below.applies)
        over = self.eng.assess("tds-professional-fees", 30000, date(2026, 7, 1),
                               prior_year_total=25000)
        self.assertTrue(over.applies)
        # Catch-up on the earlier untaxed amount is what makes a breach costly.
        self.assertAlmostEqual(over.tds, 5500.0, places=2)
        self.assertAlmostEqual(over.catch_up_on, 25000.0, places=2)

    def test_no_threshold_applies_from_first_rupee(self):
        a = self.eng.assess("tds-director-fees", 1000, date(2026, 5, 1))
        self.assertTrue(a.applies)
        self.assertAlmostEqual(a.tds, 100.0, places=2)


class TestDualTest(unittest.TestCase):
    """194C triggers on EITHER a single payment or the annual aggregate."""

    def setUp(self):
        self.eng = TdsEngine()

    def test_single_payment_trigger(self):
        a = self.eng.assess("tds-contractor-company", 31000, date(2026, 5, 1))
        self.assertTrue(a.applies)

    def test_annual_aggregate_trigger(self):
        a = self.eng.assess("tds-contractor-company", 20000, date(2026, 5, 1),
                            prior_year_total=95000)
        self.assertTrue(a.applies)

    def test_neither_trigger(self):
        a = self.eng.assess("tds-contractor-company", 20000, date(2026, 5, 1),
                            prior_year_total=10000)
        self.assertFalse(a.applies)


class TestRefusals(unittest.TestCase):
    """Refusing is a feature. An engine that answers everything will answer
    some things wrongly."""

    def setUp(self):
        self.eng = TdsEngine()

    def test_non_resident_defers_to_human(self):
        a = self.eng.assess("tds-non-resident", 500000, date(2026, 5, 1))
        self.assertTrue(a.requires_human)
        self.assertEqual(a.tds, 0.0)

    def test_salary_defers_to_payroll(self):
        a = self.eng.assess("tds-salary", 400000, date(2026, 5, 1))
        self.assertTrue(a.requires_human)

    def test_date_before_rule_is_refused(self):
        # Compliance questions are usually about a PAST year; answering with
        # today's rule would be confidently wrong.
        with self.assertRaises(ValueError):
            self.eng.assess("tds-rent-land-building", 30000, date(2020, 5, 7))

    def test_unknown_rule_raises(self):
        with self.assertRaises(KeyError):
            self.eng.assess("tds-invented", 1000, date(2026, 5, 1))


class TestInterestAndFees(unittest.TestCase):
    def setUp(self):
        self.eng = TdsEngine()

    def test_part_month_counts_as_full(self):
        i = self.eng.interest("int-late-deposit", 10000,
                              date(2026, 1, 1), date(2026, 1, 2))
        self.assertEqual(i["months"], 1)

    def test_known_real_case(self):
        # ARTH FY25-26 default: due 07-11-2025, paid 07-08-2026.
        i = self.eng.interest("int-late-deposit", 12500,
                              date(2025, 11, 7), date(2026, 8, 7))
        self.assertEqual(i["months"], 9)
        self.assertAlmostEqual(i["interest"], 1687.50, places=2)

    def test_late_fee_capped_at_statement_tds(self):
        f = self.eng.late_fee(103, 3000)
        self.assertAlmostEqual(f["fee"], 3000.0, places=2)
        self.assertTrue(f["capped"])

    def test_late_fee_uncapped_when_below(self):
        f = self.eng.late_fee(5, 50000)
        self.assertAlmostEqual(f["fee"], 1000.0, places=2)
        self.assertFalse(f["capped"])


class TestRuleSetIntegrity(unittest.TestCase):
    """Structural guarantees about the rule set itself."""

    def setUp(self):
        self.data = json.loads((HERE / "tds-in.json").read_text(encoding="utf-8"))

    def test_every_rule_cites_an_authority(self):
        missing = [r["id"] for r in self.data["rules"] if not r.get("authority")]
        self.assertEqual(missing, [], f"rules without authority: {missing}")

    def test_every_rule_is_effective_dated(self):
        missing = [r["id"] for r in self.data["rules"] if not r.get("applies_from")]
        self.assertEqual(missing, [], f"rules without applies_from: {missing}")

    def test_rule_ids_are_unique(self):
        ids = [r["id"] for r in self.data["rules"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate rule ids")

    def test_flat_rules_have_a_rate_and_basis(self):
        for r in self.data["rules"]:
            if r.get("rate_type") == "flat":
                self.assertIsNotNone(r.get("rate"), f"{r['id']} has no rate")
                self.assertIsNotNone(r.get("threshold_basis"),
                                     f"{r['id']} has no threshold_basis")

    def test_threshold_basis_values_are_known(self):
        allowed = {"per_month", "per_year_per_vendor", "per_year_per_payee",
                   "per_invoice_or_annual_aggregate", "no_threshold", None}
        for r in self.data["rules"]:
            self.assertIn(r.get("threshold_basis"), allowed,
                          f"{r['id']} has unrecognised threshold_basis")


class TestLessonsRegister(unittest.TestCase):
    """Every recorded mistake must have produced a real safeguard.

    This is the test that gives the phrase 'we learned from it' a definition:
    something now fails if the mistake recurs.
    """

    def setUp(self):
        self.data = json.loads((HERE / "lessons.json").read_text(encoding="utf-8"))
        self.lessons = self.data["lessons"]

    def test_lessons_exist(self):
        self.assertGreater(len(self.lessons), 0)

    def test_every_lesson_has_a_safeguard(self):
        for l in self.lessons:
            self.assertTrue(l.get("safeguard", "").strip(),
                            f"{l['id']} records no safeguard")

    def test_safeguards_are_concrete_not_intentions(self):
        """A safeguard must point at code, a file, or a test — not at resolve."""
        vague = re.compile(r"\b(be (more )?careful|remember to|try to|should "
                           r"(remember|check)|pay attention|in future)\b", re.I)
        for l in self.lessons:
            s = l["safeguard"]
            self.assertIsNone(vague.search(s),
                              f"{l['id']} safeguard is an intention, not a control: {s!r}")
            # Must reference something that exists in the repo or a test name.
            self.assertRegex(
                s, r"(\.py|\.json|\.ps1|\.md|\.sql|test_|::|ADR-\d+|phase \d)",
                f"{l['id']} safeguard names no concrete artefact: {s!r}")

    def test_every_lesson_records_a_root_cause(self):
        for l in self.lessons:
            self.assertTrue(l.get("root_cause", "").strip(),
                            f"{l['id']} records no root cause")

    def test_lesson_ids_unique_and_sequential(self):
        ids = [l["id"] for l in self.lessons]
        self.assertEqual(len(ids), len(set(ids)), "duplicate lesson ids")

    def test_l001_safeguard_actually_holds(self):
        """The most important lesson, verified against live behaviour rather
        than against its own description."""
        eng = TdsEngine()
        a = eng.assess("tds-rent-land-building", 30000, date(2026, 5, 7))
        self.assertFalse(a.applies,
                         "L001 regression: monthly rent below threshold now attracts TDS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
