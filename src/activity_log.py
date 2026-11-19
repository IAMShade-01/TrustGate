import os
import re
from datetime import datetime
from pathlib import Path


ENTRY_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - "
    r"(?P<status>[A-Z]+): (?P<message>.*)$"
)


def get_activity_log_path():
    local_app_data = os.environ.get("LOCALAPPDATA")
    base_dir = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
    return base_dir / "TrustGate" / "AuditLog.txt"


def parse_activity_lines(lines):
    entries = []
    for line in lines:
        match = ENTRY_PATTERN.match(line.rstrip("\r\n"))
        if not match:
            continue
        try:
            timestamp = datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        entries.append(
            {
                "timestamp": timestamp,
                "status": match.group("status"),
                "message": match.group("message"),
            }
        )
    return entries


def read_activity(log_path=None):
    path = Path(log_path) if log_path else get_activity_log_path()
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as log_file:
            return parse_activity_lines(log_file)
    except FileNotFoundError:
        return []


def append_activity(status, message, log_path=None):
    path = Path(log_path) if log_path else get_activity_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_message = " ".join(str(message).splitlines())
    entry = f"{datetime.now():%Y-%m-%d %H:%M:%S} - {status.upper()}: {safe_message}\n"
    with path.open("a", encoding="utf-8") as log_file:
        log_file.write(entry)