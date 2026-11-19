import json
import os
import sys
from pathlib import Path


APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DEFAULT_PROFILES_PATH = APP_ROOT / "config" / "company_profiles.default.json"
SOURCE_PROFILES_PATH = APP_ROOT / "config" / "company_profiles.json"


def local_profiles_path():
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
    return base / "TrustGate" / "company_profiles.json"


class CompanyProfileError(ValueError):
    pass


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
    except (OSError, json.JSONDecodeError) as error:
        raise CompanyProfileError(f"Unable to load company profiles: {error}") from error

    if not isinstance(profiles, dict) or not profiles:
        raise CompanyProfileError("Company profiles must be a non-empty JSON object.")

    for name, profile in profiles.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(profile, dict):
            raise CompanyProfileError("Each company profile must have a name and an object value.")
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