"""Tests for money, date and category parsing."""

import unittest

from tally.errors import TallyError
from tally.models import (
    format_cents,
    normalize_category,
    normalize_note,
    parse_amount,
    parse_date,
    parse_id,
)


class AmountTests(unittest.TestCase):
    def test_parses_decimal_amounts_to_cents(self):
        self.assertEqual(parse_amount("12.50"), 1250)
        self.assertEqual(parse_amount("0.01"), 1)
        self.assertEqual(parse_amount("7"), 700)

    def test_rejects_non_positive_amounts(self):
        for text in ("0", "-1.00"):
            with self.subTest(text=text), self.assertRaises(TallyError):
                parse_amount(text)

    def test_rejects_fractions_of_a_cent(self):
        with self.assertRaises(TallyError):
            parse_amount("1.005")

    def test_rejects_garbage(self):
        with self.assertRaises(TallyError):
            parse_amount("twelve")

    def test_formats_cents_with_two_places(self):
        self.assertEqual(format_cents(1250), "12.50")
        self.assertEqual(format_cents(5), "0.05")
        self.assertEqual(format_cents(-120), "-1.20")


class IdTests(unittest.TestCase):
    def test_parses_positive_ids(self):
        self.assertEqual(parse_id("1"), 1)
        self.assertEqual(parse_id(" 42 "), 42)

    def test_rejects_text_and_non_positive_ids(self):
        for text in ("", "abc", "0", "-3", "1.5"):
            with self.subTest(text=text), self.assertRaises(TallyError):
                parse_id(text)


class LabelTests(unittest.TestCase):
    def test_category_is_trimmed_and_lowercased(self):
        self.assertEqual(normalize_category("  Food "), "food")

    def test_empty_category_is_refused(self):
        with self.assertRaises(TallyError):
            normalize_category("   ")

    def test_note_is_trimmed(self):
        self.assertEqual(normalize_note("  lunch  "), "lunch")

    def test_iso_date_is_kept(self):
        self.assertEqual(parse_date("2026-10-19"), "2026-10-19")

    def test_invalid_date_is_refused(self):
        with self.assertRaises(TallyError):
            parse_date("19/10/2026")


if __name__ == "__main__":
    unittest.main()
