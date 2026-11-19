import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from activity_log import append_activity, parse_activity_lines, read_activity


class ActivityLogTests(unittest.TestCase):
    def test_parse_activity_lines_ignores_malformed_entries(self):
        entries = parse_activity_lines(
            [
                "2026-11-13 09:30:00 - SUCCESS: Login complete\n",
                "not an audit event\n",
                "2026-99-13 09:30:00 - FAILURE: Invalid date\n",
            ]
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["timestamp"], datetime(2026, 11, 13, 9, 30))
        self.assertEqual(entries[0]["status"], "SUCCESS")
        self.assertEqual(entries[0]["message"], "Login complete")

    def test_read_missing_log_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            self.assertEqual(read_activity(Path(temporary_directory) / "missing.log"), [])

    def test_append_creates_directory_and_writes_parseable_event(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "nested" / "AuditLog.txt"
            append_activity("success", "Preview enabled", log_path)

            entries = read_activity(log_path)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "SUCCESS")
        self.assertEqual(entries[0]["message"], "Preview enabled")


if __name__ == "__main__":
    unittest.main()