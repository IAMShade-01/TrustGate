import json
import os
import tempfile
from pathlib import Path


MODULES = {
    "account": ("Windows account", "Shows the current Windows account."),
    "domain": ("Domain", "Shows the current Windows domain or device context."),
    "launch": ("Launch preference", "Shows the current preview-only launch preference."),
    "computer": ("Computer name", "Shows the local computer name."),
    "activity": ("Audit events", "Counts the local TrustGate audit events."),
    "printers": ("Pending printer requests", "Counts locally saved pending printer requests."),
}
DEFAULT_WIDGETS = ("account", "domain", "launch")


class DashboardConfigError(ValueError):
    pass


class DashboardStore:
    def __init__(self, path=None):
        if path is None:
            local_app_data = os.environ.get("LOCALAPPDATA")
            base = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
            path = base / "TrustGate" / "dashboard.json"
        self.path = Path(path)

    @staticmethod
    def _validate(data):
        if not isinstance(data, dict) or data.get("version") != 1:
            raise DashboardConfigError("Dashboard configuration has an unsupported format.")
        widgets = data.get("widgets")
        if (
            not isinstance(widgets, list)
            or any(not isinstance(widget, str) or widget not in MODULES for widget in widgets)
            or len(widgets) != len(set(widgets))
        ):
            raise DashboardConfigError("Dashboard configuration contains invalid or duplicate widgets.")
        return list(widgets)

    def load(self):
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            return list(DEFAULT_WIDGETS)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise DashboardConfigError(f"Could not read dashboard configuration: {error}") from error
        return self._validate(data)

    def save(self, widgets):
        data = {"version": 1, "widgets": widgets}
        self._validate(data)
        temporary_path = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False,
            ) as file:
                temporary_path = Path(file.name)
                json.dump(data, file, indent=2)
            temporary_path.replace(self.path)
        except OSError as error:
            raise DashboardConfigError(f"Could not save dashboard configuration: {error}") from error
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
