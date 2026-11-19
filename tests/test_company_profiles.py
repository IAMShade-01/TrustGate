import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from company_profiles import (
    CompanyProfileError, DEFAULT_PROFILES_PATH, add_company_profile, export_company_profile,
    import_company_profile, load_active_profile, load_company_profiles, save_active_profile,
    save_company_profiles,
)


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

    def test_create_clone_and_switch_persist(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            profiles_path = root / "profiles.json"
            active_path = root / "active.json"
            original = {"Default": {"domain": "EXAMPLE", "printers": ["printer"], "drives": []}}
            created = add_company_profile(original, "Test Lab", {"domain": "TEST"})
            cloned = add_company_profile(created, "Clone", dict(created["Default"]))
            save_company_profiles(cloned, profiles_path)
            loaded = load_company_profiles(profiles_path)
            save_active_profile("Test Lab", loaded, active_path)
            self.assertEqual(load_active_profile(loaded, active_path), "Test Lab")
            self.assertEqual(loaded["Clone"]["printers"], ["printer"])
            with self.assertRaises(CompanyProfileError):
                add_company_profile(loaded, "test lab", {})
            with self.assertRaises(CompanyProfileError):
                save_active_profile("Missing", loaded, active_path)
            self.assertEqual(load_active_profile(loaded, active_path), "Test Lab")

    def test_encrypted_backup_round_trip_and_wrong_passphrase(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "backup.tgprofile"
            profile = {"domain": "PRIVATE-DOMAIN", "default_ou": "", "printers": [], "drives": []}
            export_company_profile(path, "Test Lab", profile, "a long passphrase")
            contents = path.read_text(encoding="utf-8")
            self.assertNotIn("PRIVATE-DOMAIN", contents)
            self.assertNotIn("Test Lab", contents)
            self.assertEqual(import_company_profile(path, "a long passphrase"), ("Test Lab", profile))
            with self.assertRaises(CompanyProfileError):
                import_company_profile(path, "incorrect passphrase")
            self.assertEqual(path.read_text(encoding="utf-8"), contents)

    def test_rejects_tampering_and_weak_export_passphrases(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "profile.tgprofile"
            with self.assertRaises(CompanyProfileError):
                export_company_profile(path, "Test", {}, "short")
            self.assertFalse(path.exists())
            export_company_profile(path, "Test", {}, "a long passphrase")
            data = json.loads(path.read_text(encoding="utf-8"))
            data["nonce"] = "AAAAAAAAAAAAAAAA"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CompanyProfileError):
                import_company_profile(path, "a long passphrase")

    def test_imports_plain_profile_json_and_rejects_invalid_data(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "profile.json"
            path.write_text(json.dumps({"name": "Lab", "profile": {"domain": "TEST"}}), encoding="utf-8")
            name, profile = import_company_profile(path)
            self.assertEqual((name, profile["domain"]), ("Lab", "TEST"))
            path.write_text(json.dumps({"name": "Lab", "profile": {"printers": "not-a-list"}}), encoding="utf-8")
            with self.assertRaises(CompanyProfileError):
                import_company_profile(path)

    def test_invalid_active_profile_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "active.json"
            path.write_text(json.dumps({"active": "Missing"}), encoding="utf-8")
            with self.assertRaises(CompanyProfileError):
                load_active_profile({"Example": {}}, path)


if __name__ == "__main__":
    unittest.main()