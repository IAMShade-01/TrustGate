import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from company_profiles import CompanyProfileError, DEFAULT_PROFILES_PATH, load_company_profiles


class CompanyProfileTests(unittest.TestCase):
    def test_loads_company_presets(self):
        profiles = load_company_profiles(DEFAULT_PROFILES_PATH)

        self.assertEqual(profiles["Example Company"]["domain"], "EXAMPLE")
        self.assertIn("Custom", profiles)

    def test_prefers_local_profile_over_bundled_defaults(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "profiles.json"
            path.write_text(json.dumps({"Local": {"domain": "LOCAL"}}), encoding="utf-8")
            with patch("company_profiles.local_profiles_path", return_value=path):
                self.assertEqual(load_company_profiles()["Local"]["domain"], "LOCAL")

    def test_rejects_invalid_printer_list(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "profiles.json"
            path.write_text(
                json.dumps({"Example": {"domain": "EXAMPLE", "printers": "not-a-list"}}),
                encoding="utf-8",
            )

            with self.assertRaises(CompanyProfileError):
                load_company_profiles(path)


if __name__ == "__main__":
    unittest.main()