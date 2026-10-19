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


if __name__ == "__main__":
    unittest.main()
