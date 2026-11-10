import base64
import hashlib
import json
import os
import uuid
from pathlib import Path

import keyring
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


SERVICE_NAME = "TrustGate"


class CredentialStoreError(RuntimeError):
    pass


class CredentialStore:
    def __init__(self, base_dir=None, keyring_api=None):
        self._keyring = keyring_api or keyring
        self._require_windows_vault = keyring_api is None and os.name == "nt"
        self._validate_keyring()

        if base_dir is None:
            data_root = os.environ.get("LOCALAPPDATA")
            if not data_root:
                data_root = Path.home() / ".local" / "share"
            base_dir = Path(data_root) / "TrustGate"

        self.base_dir = Path(base_dir)
        self.settings_path = self.base_dir / "settings.json"

    def _validate_keyring(self):
        try:
            backend = self._keyring.get_keyring()
            if backend.priority <= 0 or "Plaintext" in type(backend).__name__:
                raise CredentialStoreError(
                    "A secure operating-system credential store is unavailable."
                )
            if self._require_windows_vault and type(backend).__name__ != "WinVaultKeyring":
                raise CredentialStoreError(
                    "TrustGate requires Windows Credential Manager for secret storage."
                )
        except CredentialStoreError:
            raise
        except Exception as error:
            raise CredentialStoreError(
                "Could not initialize the operating-system credential store."
            ) from error

    def _load_settings(self):
        if not self.settings_path.exists():
            return {"device_id": str(uuid.uuid4()), "profiles": []}

        try:
            with self.settings_path.open("r", encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
            if not isinstance(settings.get("profiles"), list):
                raise ValueError("Invalid profiles list")
            return settings
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise CredentialStoreError("TrustGate settings could not be read.") from error

    def _save_settings(self, settings):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        temporary_path = self.settings_path.with_suffix(".tmp")
        try:
            with temporary_path.open("w", encoding="utf-8") as settings_file:
                json.dump(settings, settings_file, indent=2)
            temporary_path.replace(self.settings_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def get_identity(self):
        settings = self._load_settings()
        if not self.settings_path.exists():
            self._save_settings(settings)
        device_id = settings["device_id"]
        secret_name = f"identity:{device_id}:ed25519-private"
        encoded_private_key = self._keyring.get_password(SERVICE_NAME, secret_name)

        if encoded_private_key is None:
            private_key = Ed25519PrivateKey.generate()
            raw_private_key = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
            encoded_private_key = base64.b64encode(raw_private_key).decode("ascii")
            self._keyring.set_password(SERVICE_NAME, secret_name, encoded_private_key)
        else:
            try:
                raw_private_key = base64.b64decode(encoded_private_key, validate=True)
                private_key = Ed25519PrivateKey.from_private_bytes(raw_private_key)
            except (ValueError, TypeError) as error:
                raise CredentialStoreError("The TrustGate identity key is invalid.") from error

        public_key = private_key.public_key()
        public_key_text = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        ).decode("ascii")
        raw_public_key = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        fingerprint = base64.b64encode(hashlib.sha256(raw_public_key).digest())
        fingerprint = fingerprint.decode("ascii").rstrip("=")

        return {
            "device_id": device_id,
            "public_key": public_key_text,
            "fingerprint": f"SHA256:{fingerprint}",
        }

    def get_profiles(self):
        return self._load_settings()["profiles"]

    def save_profile(self, name, platform, kind, endpoint, credentials, username=""):
        name = name.strip()
        platform = platform.strip()
        endpoint = endpoint.strip()
        username = username.strip()

        if not name or not platform or not endpoint:
            raise CredentialStoreError("Name, platform, and endpoint are required.")
        if kind not in {"API", "SSH"}:
            raise CredentialStoreError("Choose API or SSH credentials.")

        if kind == "API" and not (credentials.get("api_key") or credentials.get("api_secret")):
            raise CredentialStoreError("Enter an API key or API secret.")
        if kind == "SSH" and (not username or not credentials.get("ssh_private_key")):
            raise CredentialStoreError("SSH profiles require a username and private key.")

        settings = self._load_settings()
        profile_id = str(uuid.uuid4())
        profile = {
            "id": profile_id,
            "name": name,
            "platform": platform,
            "kind": kind,
            "endpoint": endpoint,
            "username": username if kind == "SSH" else "",
        }
        stored_secrets = []

        try:
            for secret_name, secret_value in credentials.items():
                if secret_value:
                    keyring_name = f"profile:{profile_id}:{secret_name}"
                    self._keyring.set_password(SERVICE_NAME, keyring_name, secret_value)
                    stored_secrets.append(keyring_name)

            settings["profiles"].append(profile)
            self._save_settings(settings)
        except Exception as error:
            for keyring_name in stored_secrets:
                try:
                    self._keyring.delete_password(SERVICE_NAME, keyring_name)
                except Exception:
                    pass
            if isinstance(error, CredentialStoreError):
                raise
            raise CredentialStoreError("Credentials could not be saved securely.") from error

        return profile

    def delete_profile(self, profile_id):
        settings = self._load_settings()
        profiles = settings["profiles"]
        profile = next((item for item in profiles if item["id"] == profile_id), None)
        if profile is None:
            raise CredentialStoreError("The selected profile no longer exists.")

        for secret_name in ("api_key", "api_secret", "ssh_private_key", "ssh_passphrase"):
            keyring_name = f"profile:{profile_id}:{secret_name}"
            try:
                self._keyring.delete_password(SERVICE_NAME, keyring_name)
            except self._keyring.errors.PasswordDeleteError:
                pass
            except Exception as error:
                raise CredentialStoreError("Stored credentials could not be removed.") from error

        settings["profiles"] = [item for item in profiles if item["id"] != profile_id]
        self._save_settings(settings)
