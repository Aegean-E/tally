"""Fault-injection tests for the atomic ledger store (PRINCIPLE-013)."""

import errno
import io
import json
import shutil
import tempfile
import threading
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from tally import storage
from tally.errors import TallyError
from tally.models import Expense
from tally.storage import StateStore


class StoreFaultTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="tally-store-"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.path = self.temp_dir / "tally.json"
        self.store = StateStore(self.path)

    def _write(self, expenses):
        self.store.update(lambda _current: expenses)

    def test_malformed_json_recovers_from_backup(self):
        self._write([Expense(1, 500, "food", "", "2026-10-18")])
        self._write([Expense(1, 500, "food", "", "2026-10-18")])
        self.path.write_text("{broken", encoding="utf-8")
        self.assertEqual([expense.id for expense in self.store.read()], [1])

    def test_zero_byte_ledger_recovers_from_backup(self):
        self._write([Expense(1, 500, "food", "", "2026-10-18")])
        self._write([Expense(1, 500, "food", "", "2026-10-18")])
        self.path.write_text("", encoding="utf-8")
        self.assertEqual([expense.id for expense in self.store.read()], [1])

    def test_backup_is_written_before_replacement(self):
        self._write([])
        self._write([])
        self.assertTrue(self.path.with_name("tally.json.bak").exists())

    def test_unknown_version_is_refused_in_place(self):
        original = json.dumps({"version": 99, "expenses": []})
        self.path.write_text(original, encoding="utf-8")
        with self.assertRaises(TallyError):
            self.store.read()
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_insufficient_disk_space_writes_nothing(self):
        self._write([])
        usage = shutil.disk_usage(self.temp_dir)
        before = self.path.read_text(encoding="utf-8")
        with mock.patch("tally.storage.shutil.disk_usage",
                        return_value=type(usage)(usage.total, usage.used, 0)):
            with self.assertRaises(TallyError):
                self._write([])
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_concurrent_writers_lose_no_entries(self):
        def add(number):
            self.store.update(
                lambda current: current + [Expense(number, 100, "food", "", "2026-10-19")]
            )

        threads = [threading.Thread(target=add, args=(number,)) for number in range(1, 9)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(self.store.read()), 8)

    def test_replace_does_not_retry_a_non_transient_error(self):
        with mock.patch("tally.storage.os.replace",
                        side_effect=OSError(errno.ENOSPC, "No space left on device")) as replace:
            with mock.patch("tally.storage.time.sleep"):
                with self.assertRaises(TallyError):
                    self.store._replace(self.temp_dir / "temp.json")
        self.assertEqual(replace.call_count, 1)

    def test_replace_retries_a_permission_error_then_succeeds(self):
        with mock.patch("tally.storage.os.replace",
                        side_effect=[PermissionError("busy"), PermissionError("busy"), None]) as replace:
            with mock.patch("tally.storage.time.sleep"):
                self.store._replace(self.temp_dir / "temp.json")
        self.assertEqual(replace.call_count, 3)

    def test_fsync_directory_failure_is_reported(self):
        error = io.StringIO()
        with mock.patch.object(storage.os, "name", "posix"):
            with mock.patch("tally.storage.os.open", side_effect=OSError("unsupported")):
                with redirect_stderr(error):
                    self.store._fsync_directory(self.temp_dir)
        self.assertIn("[WARN]", error.getvalue())
        self.assertIn("Could not fsync directory", error.getvalue())

    def test_backup_failure_is_reported_and_the_write_continues(self):
        self._write([])
        error = io.StringIO()
        with mock.patch("tally.storage.shutil.copy2", side_effect=OSError("denied")):
            with redirect_stderr(error):
                self._write([])
        self.assertIn("[WARN]", error.getvalue())
        self.assertIn("backup", error.getvalue())
        self.assertEqual(self.store.read(), [])


if __name__ == "__main__":
    unittest.main()
