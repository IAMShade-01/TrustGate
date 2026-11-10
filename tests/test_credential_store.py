import json
import tempfile
import unittest
from pathlib import Path

from credential_store import CredentialStore, CredentialStoreError, SERVICE_NAME


class FakeBackend:
    priority = 1


class PasswordDeleteError(Exception):
    pass


class FakeKeyring:
    class errors:
        PasswordDeleteError = PasswordDeleteError

    def __init__(self):
        self.values = {}

    def get_keyring(self):
        return FakeBackend()

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        try:
            del self.values[(service, username)]
        except KeyError as error:
            raise PasswordDeleteError() from error


class CredentialStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.keyring = FakeKeyring()
        self.store = CredentialStore(
            base_dir=Path(self.temporary_directory.name),
            keyring_api=self.keyring,
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_device_identity_is_stable_and_private_key_is_not_in_settings(self):
        first_identity = self.store.get_identity()
        second_identity = self.store.get_identity()

        self.assertEqual(first_identity, second_identity)
        self.assertTrue(first_identity["public_key"].startswith("ssh-ed25519 "))
        settings_text = self.store.settings_path.read_text(encoding="utf-8")
        self.assertNotIn("PRIVATE KEY", settings_text)
        self.assertIn((SERVICE_NAME, f"identity:{first_identity['device_id']}:ed25519-private"), self.keyring.values)

    def test_api_secrets_are_only_saved_in_keyring(self):
        profile = self.store.save_profile(
            name="Production",
            platform="Example Service",
            kind="API",
            endpoint="https://api.example.test",
            credentials={"api_key": "key-value", "api_secret": "secret-value"},
        )

        settings_text = self.store.settings_path.read_text(encoding="utf-8")
        self.assertNotIn("key-value", settings_text)
        self.assertNotIn("secret-value", settings_text)
        self.assertEqual(self.store.get_profiles(), [profile])
        self.assertEqual(
            self.keyring.values[(SERVICE_NAME, f"profile:{profile['id']}:api_key")],
            "key-value",
        )
        self.assertEqual(
            self.keyring.values[(SERVICE_NAME, f"profile:{profile['id']}:api_secret")],
            "secret-value",
        )

    def test_ssh_private_key_is_saved_as_a_secret(self):
        profile = self.store.save_profile(
            name="Build host",
            platform="SSH",
            kind="SSH",
            endpoint="build.example.test:22",
            username="deploy",
            credentials={"ssh_private_key": "private-key", "ssh_passphrase": "passphrase"},
        )

        settings = json.loads(self.store.settings_path.read_text(encoding="utf-8"))
        self.assertNotIn("private-key", json.dumps(settings))
        self.assertNotIn("passphrase", json.dumps(settings))
        self.assertEqual(profile["username"], "deploy")

    def test_delete_profile_removes_metadata_and_secrets(self):
        profile = self.store.save_profile(
            name="Staging",
            platform="Example Service",
            kind="API",
            endpoint="https://api.example.test",
            credentials={"api_key": "remove-me"},
        )

        self.store.delete_profile(profile["id"])

        self.assertEqual(self.store.get_profiles(), [])
        self.assertNotIn((SERVICE_NAME, f"profile:{profile['id']}:api_key"), self.keyring.values)

    def test_invalid_profiles_are_rejected(self):
        with self.assertRaises(CredentialStoreError):
            self.store.save_profile(
                name="Missing key",
                platform="Example Service",
                kind="API",
                endpoint="https://api.example.test",
                credentials={},
            )

        self.assertEqual(self.store.get_profiles(), [])


if __name__ == "__main__":
    unittest.main()