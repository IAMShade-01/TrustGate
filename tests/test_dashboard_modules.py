import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard_modules import DEFAULT_WIDGETS, DashboardConfigError, DashboardStore


class DashboardStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "nested" / "dashboard.json"
        self.store = DashboardStore(self.path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_default_and_persisted_layouts(self):
        self.assertEqual(self.store.load(), list(DEFAULT_WIDGETS))
        self.store.save(["activity", "account", "printers"])
        self.assertEqual(DashboardStore(self.path).load(), ["activity", "account", "printers"])
        self.store.save([])
        self.assertEqual(self.store.load(), [])

    def test_invalid_layout_does_not_replace_saved_data(self):
        self.store.save(["account"])
        original = self.path.read_text(encoding="utf-8")
        for widgets in (["account", "account"], ["unknown"], [None]):
            with self.subTest(widgets=widgets), self.assertRaises(DashboardConfigError):
                self.store.save(widgets)
            self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_corrupt_or_future_configuration_is_reported(self):
        self.path.parent.mkdir(parents=True)
        for contents in ("{", json.dumps({"version": 2, "widgets": ["account"]})):
            self.path.write_text(contents, encoding="utf-8")
            with self.subTest(contents=contents), self.assertRaises(DashboardConfigError):
                self.store.load()
            self.assertEqual(self.path.read_text(encoding="utf-8"), contents)

    def test_failed_write_preserves_previous_configuration(self):
        self.store.save(["account"])
        with patch.object(Path, "replace", side_effect=OSError("disk error")):
            with self.assertRaisesRegex(DashboardConfigError, "disk error"):
                self.store.save(["domain"])
        self.assertEqual(self.store.load(), ["account"])
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])


if __name__ == "__main__":
    unittest.main()
