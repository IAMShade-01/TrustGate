import base64
import binascii
import json
import os
import sys
import tempfile
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DEFAULT_PROFILES_PATH = APP_ROOT / "config" / "company_profiles.default.json"
SOURCE_PROFILES_PATH = APP_ROOT / "config" / "company_profiles.json"


def local_profiles_path():
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
    return base / "TrustGate" / "company_profiles.json"


class CompanyProfileError(ValueError):
    pass


def _validate_profiles(profiles):
    if not isinstance(profiles, dict) or not profiles:
        raise CompanyProfileError("Company profiles must be a non-empty JSON object.")

    names = set()
    for name, profile in profiles.items():
        if (
            not isinstance(name, str) or not name.strip() or name != name.strip()
            or len(name) > 120 or any(ord(char) < 32 for char in name)
            or not isinstance(profile, dict)
        ):
            raise CompanyProfileError("Each company profile must have a valid name and an object value.")
        if name.casefold() in names:
            raise CompanyProfileError("Company profile names must be unique.")
        names.add(name.casefold())
        for field in ("domain", "default_ou"):
            if not isinstance(profile.get(field, ""), str):
                raise CompanyProfileError(f"{name}: {field} must be a string.")
        for field in ("printers", "drives"):
            values = profile.get(field, [])
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise CompanyProfileError(f"{name}: {field} must be a list of strings.")
            profile[field] = values
        profile.setdefault("domain", "")
        profile.setdefault("default_ou", "")
    return profiles


def load_company_profiles(path=None):
    if path is None:
        local_path = local_profiles_path()
        if local_path.exists():
            path = local_path
        elif not getattr(sys, "frozen", False) and SOURCE_PROFILES_PATH.exists():
            path = SOURCE_PROFILES_PATH
        else:
            path = DEFAULT_PROFILES_PATH
    try:
        profiles = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CompanyProfileError(f"Unable to load company profiles: {error}") from error
    return _validate_profiles(profiles)


def _write_json(path, data):
    path = Path(path)
    temporary_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary_path = Path(file.name)
            json.dump(data, file, indent=2, ensure_ascii=False)
        temporary_path.replace(path)
    except (OSError, TypeError, ValueError) as error:
        raise CompanyProfileError(f"Could not save company profile: {error}") from error
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def save_company_profiles(profiles, path=None):
    _validate_profiles(profiles)
    _write_json(path or local_profiles_path(), profiles)


def active_profile_path():
    return local_profiles_path().with_name("active_company.json")


def load_active_profile(profiles, path=None):
    path = Path(path or active_profile_path())
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return next(iter(profiles))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CompanyProfileError(f"Could not read the active profile: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("active"), str) or data["active"] not in profiles:
        raise CompanyProfileError("The saved active company profile is invalid or no longer exists. Select a profile.")
    return data["active"]


def save_active_profile(name, profiles, path=None):
    if name not in profiles:
        raise CompanyProfileError("The selected company profile does not exist.")
    _write_json(path or active_profile_path(), {"active": name})


def add_company_profile(profiles, name, profile):
    name = name.strip()
    if any(existing.casefold() == name.casefold() for existing in profiles):
        raise CompanyProfileError("A company profile with that name already exists.")
    updated = dict(profiles)
    updated[name] = dict(profile)
    _validate_profiles(updated)
    return updated


PROFILE_FORMAT = "trustgate-company-profile"
PROFILE_AAD = b"TrustGate company profile v1"
MAX_PROFILE_FILE_SIZE = 1024 * 1024


def _profile_key(passphrase, salt):
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(passphrase.encode("utf-8"))


def export_company_profile(path, name, profile, passphrase):
    if len(passphrase) < 12:
        raise CompanyProfileError("Use a passphrase of at least 12 characters.")
    _validate_profiles({name: dict(profile)})
    salt = os.urandom(16)
    nonce = os.urandom(12)
    plaintext = json.dumps({"name": name, "profile": profile}, ensure_ascii=False).encode("utf-8")
    ciphertext = AESGCM(_profile_key(passphrase, salt)).encrypt(nonce, plaintext, PROFILE_AAD)
    data = {
        "format": PROFILE_FORMAT, "version": 1,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    if len(json.dumps(data).encode("utf-8")) > MAX_PROFILE_FILE_SIZE:
        raise CompanyProfileError("The profile is too large to export.")
    _write_json(path, data)


def import_company_profile(path, passphrase=None):
    try:
        with Path(path).open("rb") as file:
            contents = file.read(MAX_PROFILE_FILE_SIZE + 1)
        if len(contents) > MAX_PROFILE_FILE_SIZE:
            raise CompanyProfileError("The profile file is too large.")
        data = json.loads(contents.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CompanyProfileError(f"Could not read profile file: {error}") from error
    if not isinstance(data, dict):
        raise CompanyProfileError("The profile file has an invalid format.")
    if data.get("format") == PROFILE_FORMAT:
        if data.get("version") != 1:
            raise CompanyProfileError("The encrypted profile version is unsupported.")
        if not passphrase:
            raise CompanyProfileError("A passphrase is required for this encrypted profile.")
        try:
            salt = base64.b64decode(data["salt"], validate=True)
            nonce = base64.b64decode(data["nonce"], validate=True)
            ciphertext = base64.b64decode(data["ciphertext"], validate=True)
            if len(salt) != 16 or len(nonce) != 12 or len(ciphertext) < 16:
                raise ValueError("Invalid encrypted profile fields")
            plaintext = AESGCM(_profile_key(passphrase, salt)).decrypt(nonce, ciphertext, PROFILE_AAD)
            data = json.loads(plaintext.decode("utf-8"))
        except (KeyError, TypeError, ValueError, binascii.Error, UnicodeError, json.JSONDecodeError, InvalidTag) as error:
            raise CompanyProfileError("Incorrect passphrase or invalid encrypted profile.") from error
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or not isinstance(data.get("profile"), dict):
        raise CompanyProfileError("The profile file must contain a name and profile object.")
    name = data["name"]
    profile = _validate_profiles({name: data["profile"]})[name]
    return name, profile