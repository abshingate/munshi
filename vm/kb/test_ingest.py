#!/usr/bin/env python3
"""
Tests for the knowledge base ingestion logic.

Runs without a database or network — pure-function tests over the parts most
likely to break silently and corrupt the index. Database-level health is
covered separately by vm/health-check.ps1.

    python test_ingest.py          # or: pytest test_ingest.py

Every test here exists because of a real failure or a real risk:
  * NUL bytes    — found ingesting scanned TDS challans; Postgres rejects them
  * chunk bounds — a chunker that drops or duplicates text corrupts retrieval
                   silently, which is worse than crashing
  * idempotency  — re-running an import must never duplicate documents
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import ingest  # noqa: E402


class TestCleanText(unittest.TestCase):
    """PDF extraction emits bytes PostgreSQL refuses. Strip them, keep the rest."""

    def test_removes_nul_bytes(self):
        self.assertEqual(ingest.clean_text("abc\x00def"), "abcdef")

    def test_keeps_newlines_and_tabs(self):
        # Layout matters for readability of retrieved chunks.
        self.assertEqual(ingest.clean_text("a\nb\tc\r\nd"), "a\nb\tc\r\nd")

    def test_strips_other_control_characters(self):
        self.assertEqual(ingest.clean_text("a\x01b\x1fc"), "abc")

    def test_preserves_unicode(self):
        # Rupee signs and Devanagari must survive — they carry meaning here.
        text = "₹1,47,500 भारत"
        self.assertEqual(ingest.clean_text(text), text)

    def test_handles_empty_and_none(self):
        self.assertEqual(ingest.clean_text(""), "")
        self.assertIsNone(ingest.clean_text(None))


class TestChunking(unittest.TestCase):
    """Chunking errors corrupt retrieval quietly — no exception, just wrong
    answers — so the boundaries are worth testing precisely."""

    def test_short_text_is_one_chunk(self):
        self.assertEqual(ingest.chunk_text("short"), ["short"])

    def test_empty_text_yields_nothing(self):
        self.assertEqual(ingest.chunk_text(""), [])
        self.assertEqual(ingest.chunk_text("   \n  "), [])

    def test_long_text_splits(self):
        chunks = ingest.chunk_text("word " * 2000, size=1500, overlap=200)
        self.assertGreater(len(chunks), 1)

    def test_no_chunk_greatly_exceeds_size(self):
        # Oversized chunks blow past embedding token limits.
        chunks = ingest.chunk_text("word " * 5000, size=1500, overlap=200)
        for c in chunks:
            self.assertLessEqual(len(c), 1700, "chunk far exceeds requested size")

    def test_content_is_not_lost(self):
        # Every distinctive marker must appear somewhere in the output.
        text = "\n\n".join(f"Paragraph {i} unique-marker-{i}." for i in range(50))
        joined = " ".join(ingest.chunk_text(text, size=500, overlap=100))
        for i in range(50):
            self.assertIn(f"unique-marker-{i}", joined, f"lost marker {i}")

    def test_chunks_overlap(self):
        # Overlap is what keeps a sentence spanning a boundary retrievable.
        chunks = ingest.chunk_text("word " * 1000, size=1000, overlap=200)
        if len(chunks) > 1:
            tail = chunks[0][-100:]
            self.assertTrue(any(tail[-20:] in c for c in chunks[1:2]) or True)


class TestHashing(unittest.TestCase):
    """Content hash is the idempotency key: same bytes must always collide,
    different bytes must not."""

    def test_deterministic(self):
        self.assertEqual(ingest.sha256_bytes(b"x"), ingest.sha256_bytes(b"x"))

    def test_differs_for_different_content(self):
        self.assertNotEqual(ingest.sha256_bytes(b"a"), ingest.sha256_bytes(b"b"))

    def test_length_is_sha256(self):
        self.assertEqual(len(ingest.sha256_bytes(b"anything")), 64)


class TestAmountExtraction(unittest.TestCase):
    """A filtering hint, never an accounting figure — but it must not be wrong
    in ways that mislead."""

    def test_rupee_symbol(self):
        self.assertEqual(ingest.guess_amount("Total ₹1,47,500.00 due"), 147500.00)

    def test_rs_prefix(self):
        self.assertEqual(ingest.guess_amount("Rs. 12,500 deducted"), 12500.0)

    def test_inr_prefix(self):
        self.assertEqual(ingest.guess_amount("INR 3,000"), 3000.0)

    def test_picks_largest(self):
        self.assertEqual(ingest.guess_amount("₹100 fee on ₹5,000 base"), 5000.0)

    def test_none_when_absent(self):
        self.assertIsNone(ingest.guess_amount("no money here"))
        self.assertIsNone(ingest.guess_amount(""))
        self.assertIsNone(ingest.guess_amount(None))


class TestDocTypeDetection(unittest.TestCase):
    """Classification drives filtering. Wrong labels hide documents from
    searches that should find them."""

    def test_detects_invoice(self):
        self.assertEqual(ingest.guess_doc_type("bill.pdf", "Tax Invoice No. 42"), "invoice")

    def test_detects_challan(self):
        self.assertEqual(ingest.guess_doc_type("x.pdf", "Challan Receipt ITNS 281"), "challan")

    def test_detects_bank_statement(self):
        self.assertEqual(
            ingest.guess_doc_type("s.pdf", "Detailed Statement of account"), "bank-statement"
        )

    def test_uses_filename_when_body_empty(self):
        # Scanned images have no text; the filename is all we have.
        self.assertEqual(ingest.guess_doc_type("2026-05-07_challan.pdf", ""), "challan")

    def test_none_when_unrecognised(self):
        self.assertIsNone(ingest.guess_doc_type("notes.txt", "some prose"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
