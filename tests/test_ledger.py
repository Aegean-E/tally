"""Tests for the ledger operations on top of the state store."""

import shutil
import tempfile
import unittest
from pathlib import Path

from tally.errors import TallyError
from tally.ledger import Ledger
from tally.models import Expense
from tally.storage import StateStore


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="tally-ledger-"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.ledger = Ledger(StateStore(self.temp_dir / "tally.json"))

    def test_add_assigns_consecutive_ids(self):
        first = self.ledger.add(1250, "food", "lunch", "2026-10-18")
        second = self.ledger.add(300, "transport", "", "2026-10-19")
        self.assertEqual((first.id, second.id), (1, 2))
        self.assertEqual(self.ledger.entries()[0], Expense(1, 1250, "food", "lunch", "2026-10-18"))

    def test_entries_are_oldest_first(self):
        self.ledger.add(300, "transport", "", "2026-10-19")
        self.ledger.add(1250, "food", "", "2026-10-18")
        self.assertEqual([expense.spent_on for expense in self.ledger.entries()],
                         ["2026-10-18", "2026-10-19"])

    def test_entries_filter_by_category(self):
        self.ledger.add(1250, "food", "", "2026-10-18")
        self.ledger.add(300, "transport", "", "2026-10-19")
        self.assertEqual([expense.category for expense in self.ledger.entries("food")], ["food"])

    def test_summary_totals_each_category(self):
        self.ledger.add(1250, "food", "", "2026-10-18")
        self.ledger.add(250, "food", "", "2026-10-19")
        self.ledger.add(300, "transport", "", "2026-10-19")
        self.assertEqual(self.ledger.summary(), {"food": 1500, "transport": 300})
        self.assertEqual(self.ledger.total(), 1800)

    def test_entries_survive_a_new_ledger_instance(self):
        self.ledger.add(1250, "food", "", "2026-10-18")
        reopened = Ledger(StateStore(self.temp_dir / "tally.json"))
        self.assertEqual(reopened.total(), 1250)

    def test_edit_changes_only_the_given_fields(self):
        self.ledger.add(1250, "food", "lunch", "2026-10-18")
        edited = self.ledger.edit(1, amount_cents=999)
        self.assertEqual(edited, Expense(1, 999, "food", "lunch", "2026-10-18"))
        self.assertEqual(self.ledger.entries(), [edited])

    def test_edit_can_clear_a_note(self):
        self.ledger.add(1250, "food", "lunch", "2026-10-18")
        self.assertEqual(self.ledger.edit(1, note="").note, "")

    def test_edit_without_fields_is_refused(self):
        self.ledger.add(1250, "food", "lunch", "2026-10-18")
        with self.assertRaises(TallyError):
            self.ledger.edit(1)
        self.assertEqual(self.ledger.total(), 1250)

    def test_edit_missing_id_changes_nothing(self):
        self.ledger.add(1250, "food", "lunch", "2026-10-18")
        with self.assertRaises(TallyError):
            self.ledger.edit(99, amount_cents=1)
        self.assertEqual(self.ledger.entries()[0].amount_cents, 1250)

    def test_edit_survives_a_new_ledger_instance(self):
        self.ledger.add(1250, "food", "lunch", "2026-10-18")
        self.ledger.edit(1, amount_cents=999)
        reopened = Ledger(StateStore(self.temp_dir / "tally.json"))
        self.assertEqual(reopened.total(), 999)

    def test_remove_drops_only_the_named_id(self):
        self.ledger.add(1250, "food", "", "2026-10-18")
        self.ledger.add(300, "transport", "", "2026-10-19")
        self.ledger.add(500, "food", "", "2026-10-19")
        removed = self.ledger.remove(2)
        self.assertEqual(removed, Expense(2, 300, "transport", "", "2026-10-19"))
        self.assertEqual([expense.id for expense in self.ledger.entries()], [1, 3])

    def test_remove_missing_id_changes_nothing(self):
        self.ledger.add(1250, "food", "", "2026-10-18")
        with self.assertRaises(TallyError):
            self.ledger.remove(99)
        self.assertEqual(self.ledger.total(), 1250)

    def test_next_id_follows_the_highest_remaining_entry(self):
        self.ledger.add(1250, "food", "", "2026-10-18")
        self.ledger.add(300, "transport", "", "2026-10-19")
        self.ledger.add(500, "food", "", "2026-10-19")
        self.ledger.remove(2)
        self.assertEqual(self.ledger.add(700, "food", "", "2026-10-20").id, 4)
        self.ledger.remove(4)
        self.assertEqual(self.ledger.add(900, "food", "", "2026-10-20").id, 4)

    def test_entries_filter_by_date_range(self):
        self.ledger.add(100, "general", "september", "2026-09-30")
        self.ledger.add(200, "general", "early october", "2026-10-05")
        self.ledger.add(300, "general", "mid october", "2026-10-15")
        self.ledger.add(400, "general", "november", "2026-11-01")

        october = self.ledger.entries(from_date="2026-10-01", to_date="2026-10-31")
        self.assertEqual([e.note for e in october], ["early october", "mid october"])

        from_mid_oct = self.ledger.entries(from_date="2026-10-15")
        self.assertEqual([e.note for e in from_mid_oct], ["mid october", "november"])

        up_to_early_oct = self.ledger.entries(to_date="2026-10-05")
        self.assertEqual([e.note for e in up_to_early_oct], ["september", "early october"])

    def test_entries_filter_by_category_and_date_range(self):
        self.ledger.add(100, "food", "lunch", "2026-10-05")
        self.ledger.add(200, "transport", "bus", "2026-10-05")
        self.ledger.add(300, "food", "dinner", "2026-11-01")

        filtered = self.ledger.entries(category="food", from_date="2026-10-01", to_date="2026-10-31")
        self.assertEqual([e.note for e in filtered], ["lunch"])

    def test_summary_filters_by_date_range(self):
        self.ledger.add(1000, "food", "lunch", "2026-10-05")
        self.ledger.add(500, "transport", "bus", "2026-10-06")
        self.ledger.add(2000, "food", "dinner", "2026-11-01")

        october_summary = self.ledger.summary(from_date="2026-10-01", to_date="2026-10-31")
        self.assertEqual(october_summary, {"food": 1000, "transport": 500})
        self.assertEqual(self.ledger.total(from_date="2026-10-01", to_date="2026-10-31"), 1500)


if __name__ == "__main__":
    unittest.main()
