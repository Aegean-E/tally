"""End-to-end tests of the command-line interface through `main`."""

import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tally.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="tally-cli-"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.db = str(self.temp_dir / "tally.json")

    def run_cli(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--db", self.db, *arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_add_then_list_then_summary(self):
        code, output, _ = self.run_cli(
            "add", "12.50", "--category", "Food", "--note", "lunch", "--date", "2026-10-19"
        )
        self.assertEqual(code, 0)
        self.assertIn("Added #1: 12.50 [food]", output)

        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("#1", output)
        self.assertIn("lunch", output)

        code, output, _ = self.run_cli("summary")
        self.assertEqual(code, 0)
        self.assertIn("food", output)
        self.assertIn("12.50", output)
        self.assertIn("total", output)

    def test_list_on_empty_ledger(self):
        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("No expenses recorded.", output)

    def test_edit_updates_every_given_field(self):
        self.run_cli(
            "add", "12.50", "--category", "Food", "--note", "lunch", "--date", "2026-10-18"
        )
        code, output, _ = self.run_cli(
            "edit", "1", "--amount", "9.99", "--category", "Travel",
            "--note", "taxi", "--date", "2026-10-20",
        )
        self.assertEqual(code, 0)
        self.assertIn("Updated #1: 9.99 [travel] on 2026-10-20  taxi", output)

        code, listing, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("travel", listing)
        self.assertIn("taxi", listing)
        self.assertIn("9.99", listing)

        code, summary, _ = self.run_cli("summary")
        self.assertEqual(code, 0)
        self.assertIn("travel", summary)
        self.assertIn("9.99", summary)
        self.assertNotIn("food", summary)

    def test_edit_can_clear_a_note(self):
        self.run_cli("add", "12.50", "--note", "lunch")
        code, _, _ = self.run_cli("edit", "1", "--note", "")
        self.assertEqual(code, 0)
        _, listing, _ = self.run_cli("list")
        self.assertNotIn("lunch", listing)

    def test_edit_without_fields_reports_why_and_fix(self):
        self.run_cli("add", "12.50")
        code, _, error = self.run_cli("edit", "1")
        self.assertEqual(code, 1)
        self.assertIn("Error:", error)
        self.assertIn("Why:", error)
        self.assertIn("Fix:", error)

    def test_edit_invalid_amount_reports_why_and_fix(self):
        self.run_cli("add", "12.50")
        code, _, error = self.run_cli("edit", "1", "--amount", "nope")
        self.assertEqual(code, 1)
        self.assertIn("Error:", error)
        self.assertIn("Why:", error)
        self.assertIn("Fix:", error)

    def test_edit_missing_id_reports_why_and_fix(self):
        code, _, error = self.run_cli("edit", "99", "--amount", "1.00")
        self.assertEqual(code, 1)
        self.assertIn("Error:", error)
        self.assertIn("Why:", error)
        self.assertIn("Fix:", error)

    def test_remove_deletes_one_entry(self):
        self.run_cli("add", "12.50", "--category", "food")
        self.run_cli("add", "3.00", "--category", "transport")
        code, output, _ = self.run_cli("remove", "1")
        self.assertEqual(code, 0)
        self.assertIn("Removed #1: 12.50 [food]", output)

        code, listing, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertNotIn("#1", listing)
        self.assertIn("#2", listing)

        code, summary, _ = self.run_cli("summary")
        self.assertEqual(code, 0)
        self.assertNotIn("food", summary)
        self.assertIn("transport", summary)

    def test_remove_bad_id_reports_why_and_fix(self):
        code, _, error = self.run_cli("remove", "nope")
        self.assertEqual(code, 1)
        self.assertIn("Error:", error)
        self.assertIn("Why:", error)
        self.assertIn("Fix:", error)

    def test_remove_missing_id_reports_why_and_fix(self):
        code, _, error = self.run_cli("remove", "99")
        self.assertEqual(code, 1)
        self.assertIn("Error:", error)
        self.assertIn("Why:", error)
        self.assertIn("Fix:", error)

    def test_invalid_amount_reports_why_and_fix(self):
        code, _, error = self.run_cli("add", "nope")
        self.assertEqual(code, 1)
        self.assertIn("Error:", error)
        self.assertIn("Why:", error)
        self.assertIn("Fix:", error)

    def test_missing_command_is_argument_misuse(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(["--db", self.db])
        self.assertEqual(raised.exception.code, 2)


    def test_list_filter_by_month(self):
        self.run_cli("add", "10.00", "--date", "2026-09-30", "--note", "sept")
        self.run_cli("add", "20.00", "--date", "2026-10-15", "--note", "oct")
        self.run_cli("add", "30.00", "--date", "2026-11-01", "--note", "nov")
        code, output, _ = self.run_cli("list", "--month", "2026-10")
        self.assertEqual(code, 0)
        self.assertIn("oct", output)
        self.assertNotIn("sept", output)
        self.assertNotIn("nov", output)

    def test_list_filter_by_date_range(self):
        self.run_cli("add", "10.00", "--date", "2026-10-01", "--note", "early-item")
        self.run_cli("add", "20.00", "--date", "2026-10-10", "--note", "mid-item")
        self.run_cli("add", "30.00", "--date", "2026-10-20", "--note", "late-item")
        code, output, _ = self.run_cli("list", "--from", "2026-10-05", "--to", "2026-10-15")
        self.assertEqual(code, 0)
        self.assertIn("mid-item", output)
        self.assertNotIn("early-item", output)
        self.assertNotIn("late-item", output)

    def test_summary_filter_by_month(self):
        self.run_cli("add", "10.00", "--category", "food", "--date", "2026-09-30")
        self.run_cli("add", "25.00", "--category", "food", "--date", "2026-10-15")
        self.run_cli("add", "15.00", "--category", "transport", "--date", "2026-10-20")
        self.run_cli("add", "40.00", "--category", "food", "--date", "2026-11-01")
        code, output, _ = self.run_cli("summary", "--month", "2026-10")
        self.assertEqual(code, 0)
        self.assertIn("food", output)
        self.assertIn("25.00", output)
        self.assertIn("transport", output)
        self.assertIn("15.00", output)
        self.assertIn("40.00", output)  # total

    def test_summary_filter_by_date_range(self):
        self.run_cli("add", "10.00", "--category", "food", "--date", "2026-10-01")
        self.run_cli("add", "25.00", "--category", "food", "--date", "2026-10-10")
        self.run_cli("add", "30.00", "--category", "food", "--date", "2026-10-25")
        code, output, _ = self.run_cli("summary", "--from", "2026-10-05", "--to", "2026-10-15")
        self.assertEqual(code, 0)
        self.assertIn("25.00", output)
        self.assertNotIn("65.00", output)

    def test_list_month_conflict_reports_why_and_fix(self):
        code, _, error = self.run_cli("list", "--month", "2026-10", "--from", "2026-10-01")
        self.assertEqual(code, 1)
        self.assertIn("Error:", error)
        self.assertIn("Why:", error)
        self.assertIn("Fix:", error)

    def test_summary_start_after_end_reports_why_and_fix(self):
        code, _, error = self.run_cli("summary", "--from", "2026-10-20", "--to", "2026-10-10")
        self.assertEqual(code, 1)
        self.assertIn("Error:", error)
        self.assertIn("Why:", error)
        self.assertIn("Fix:", error)

    def test_list_invalid_month_reports_why_and_fix(self):
        code, _, error = self.run_cli("list", "--month", "bad-month")
        self.assertEqual(code, 1)
        self.assertIn("Error:", error)
        self.assertIn("Why:", error)
        self.assertIn("Fix:", error)


if __name__ == "__main__":
    unittest.main()
