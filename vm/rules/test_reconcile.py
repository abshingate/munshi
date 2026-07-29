#!/usr/bin/env python3
"""
Tests for statement parsing.

The asymmetry that shapes these tests: failing to read a transaction is
recoverable — re-read the statement. INVENTING one is not, because nothing
downstream can distinguish it from a real line. So the parser is deliberately
strict, and these tests hold it there.

Every noise case below was observed in real output, not imagined.

    python3 test_reconcile.py
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import reconcile  # noqa: E402


class TestRealTransactions(unittest.TestCase):
    """Genuine lines must still parse after the noise filters."""

    def test_tds_challan_line(self):
        line = "8 06/Mar/2026 GIB/002060223600/DTAX /260306000031 5500.00 12345.00"
        got = reconcile.parse_statement_text(line)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["date"], date(2026, 3, 6))

    def test_fd_closure_line(self):
        line = "5 06/Mar/2026 239010020993: Closure Proceeds 4800000.00 5000000.00"
        got = reconcile.parse_statement_text(line)
        self.assertEqual(len(got), 1)
        self.assertIn(4800000.00, got[0]["amounts"])

    def test_interest_credit_line(self):
        line = "6 06/Mar/2026 Int on FD/RD XXX0993 Tds:740. 6657.00 18002.00"
        self.assertEqual(len(reconcile.parse_statement_text(line)), 1)


class TestNoiseRejection(unittest.TestCase):
    """Page furniture that contains a date and a number, but is not money."""

    def test_printed_timestamp(self):
        # Became a ₹12.44 "transaction" on the first real run.
        self.assertEqual(
            reconcile.parse_statement_text("Date And Time : 09/03/2026 12.44 PM"), [])

    def test_lien_balance_footer(self):
        self.assertEqual(
            reconcile.parse_statement_text(
                "Balance Details as on: 09/03/2026 Lien Balance: 0.00"), [])

    def test_closing_balance_footer(self):
        self.assertEqual(
            reconcile.parse_statement_text(
                "Closing Balance as on 31/03/2026 : 1,23,456.78"), [])

    def test_statement_period_header(self):
        self.assertEqual(
            reconcile.parse_statement_text(
                "Statement Period : 01/04/2025 to 31/03/2026 Page 1 of 12"), [])

    def test_all_zero_amounts_rejected(self):
        self.assertEqual(
            reconcile.parse_statement_text(
                "12 01/04/2025 Some description here 0.00 0.00"), [])


class TestIdempotency(unittest.TestCase):
    """Re-loading a statement must never duplicate rows."""

    def test_same_line_same_hash(self):
        a = reconcile.row_hash("123", date(2026, 3, 6), "desc", 100.0, None)
        b = reconcile.row_hash("123", date(2026, 3, 6), "desc", 100.0, None)
        self.assertEqual(a, b)

    def test_identical_amounts_same_day_stay_distinct(self):
        # Two ₹400 fees on one day are common; collapsing them would silently
        # drop a real transaction, so the description is part of the key.
        a = reconcile.row_hash("123", date(2026, 3, 6), "fee A", 400.0, None)
        b = reconcile.row_hash("123", date(2026, 3, 6), "fee B", 400.0, None)
        self.assertNotEqual(a, b)


class TestFinancialYear(unittest.TestCase):
    def test_april_starts_new_fy(self):
        self.assertEqual(reconcile.fy_of(date(2026, 4, 1)), "2026-27")

    def test_march_ends_fy(self):
        self.assertEqual(reconcile.fy_of(date(2026, 3, 31)), "2025-26")


if __name__ == "__main__":
    unittest.main(verbosity=2)
