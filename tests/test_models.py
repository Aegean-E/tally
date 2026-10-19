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
    parse_month,
    resolve_date_range,
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


class MonthTests(unittest.TestCase):
    def test_parses_iso_month(self):
        self.assertEqual(parse_month("2026-10"), "2026-10")
        self.assertEqual(parse_month(" 2026-05 "), "2026-05")

    def test_rejects_invalid_months(self):
        for text in ("", "invalid", "2026-13", "2026-00", "2026-5", "oct-2026", "2026/10"):
            with self.subTest(text=text), self.assertRaises(TallyError):
                parse_month(text)


class DateRangeTests(unittest.TestCase):
    def test_resolve_date_range_month(self):
        self.assertEqual(
            resolve_date_range(None, None, "2026-02"),
            ("2026-02-01", "2026-02-28"),
        )
        self.assertEqual(
            resolve_date_range(None, None, "2024-02"),
            ("2024-02-01", "2024-02-29"),
        )
        self.assertEqual(
            resolve_date_range(None, None, "2026-10"),
            ("2026-10-01", "2026-10-31"),
        )

    def test_resolve_date_range_from_to(self):
        self.assertEqual(
            resolve_date_range("2026-10-01", "2026-10-15", None),
            ("2026-10-01", "2026-10-15"),
        )
        self.assertEqual(
            resolve_date_range("2026-10-01", None, None),
            ("2026-10-01", None),
        )
        self.assertEqual(
            resolve_date_range(None, "2026-10-15", None),
            (None, "2026-10-15"),
        )
        self.assertEqual(
            resolve_date_range(None, None, None),
            (None, None),
        )

    def test_resolve_date_range_from_after_to(self):
        with self.assertRaises(TallyError):
            resolve_date_range("2026-10-20", "2026-10-10", None)

    def test_resolve_date_range_month_conflict(self):
        with self.assertRaises(TallyError):
            resolve_date_range("2026-10-01", None, "2026-10")
        with self.assertRaises(TallyError):
            resolve_date_range(None, "2026-10-31", "2026-10")
        with self.assertRaises(TallyError):
            resolve_date_range("2026-10-01", "2026-10-31", "2026-10")


if __name__ == "__main__":
    unittest.main()
