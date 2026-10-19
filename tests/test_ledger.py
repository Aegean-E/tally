"""Tests for the ledger operations on top of the state store."""

import shutil
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
