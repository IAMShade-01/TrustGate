import json
import os
import sys
import textwrap
import uuid
from datetime import date
from pathlib import Path


APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DEFAULT_TEMPLATE_PATH = APP_ROOT / "config" / "printer_request_template.txt"
VALID_STATUSES = {"Pending", "Complete", "Failed"}


class PrinterRequestError(ValueError):
    pass


def app_data_dir():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "TrustGate"
    return Path.home() / ".local" / "share" / "TrustGate"


def render_request(fields, template):
    values = dict(fields)
    values.setdefault("date", date.today().strftime("%m/%d/%Y"))
    try:
        return template.format_map(values).strip()
    except (KeyError, ValueError) as error:
        raise PrinterRequestError(f"Request template could not be rendered: {error}") from error


class PrinterRequestStore:
    def __init__(self, requests_path=None, template_path=None):
        data_dir = app_data_dir()
        self.requests_path = Path(requests_path or data_dir / "printer_requests.json")
        self.template_path = Path(template_path or data_dir / "printer_request_template.txt")
        self.default_template_path = DEFAULT_TEMPLATE_PATH

    def load_template(self):
        path = self.template_path if self.template_path.exists() else self.default_template_path
        try:
            return path.read_text(encoding="utf-8")
        except OSError as error:
            raise PrinterRequestError(f"Could not read printer request template: {error}") from error

    def save_template(self, template):
        if not isinstance(template, str) or not template.strip():
            raise PrinterRequestError("The printer request template cannot be empty.")
        self._write_text(self.template_path, template)

    def list_requests(self):
        if not self.requests_path.exists():
            return []
        try:
            requests = json.loads(self.requests_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PrinterRequestError("The local printer request database could not be read.") from error
        if not isinstance(requests, list):
            raise PrinterRequestError("The local printer request database has an invalid format.")
        return requests

    def create_request(self, fields):
        required = (
            "computer_name", "user_name", "location", "department", "printer_type",
            "printer_team_contact", "reason", "requested_by", "requested_by_title",
        )
        normalized = {key: str(fields.get(key, "")).strip() for key in required}
        missing = [key.replace("_", " ") for key, value in normalized.items() if not value]
        if missing:
            raise PrinterRequestError("Required fields are missing: " + ", ".join(missing))

        created = date.today().isoformat()
        normalized["date"] = date.today().strftime("%m/%d/%Y")
        request = {
            "Id": str(uuid.uuid4()),
            "ComputerName": normalized["computer_name"],
            "RequestType": "Printer",
            "Status": "Pending",
            "DateCreated": created,
            "Fields": normalized,
            "RequestText": render_request(normalized, self.load_template()),
        }
        requests = self.list_requests()
        requests.append(request)
        self._save_requests(requests)
        return request

    def update_status(self, request_id, status):
        if status not in VALID_STATUSES:
            raise PrinterRequestError(f"Status must be one of: {', '.join(sorted(VALID_STATUSES))}.")
        requests = self.list_requests()
        for request in requests:
            if request.get("Id") == request_id:
                request["Status"] = status
                request["DateUpdated"] = date.today().isoformat()
                self._save_requests(requests)
                return request
        raise PrinterRequestError("The selected printer request was not found.")

    def latest_for_computer(self, computer_name):
        matches = [
            request for request in self.list_requests()
            if request.get("ComputerName", "").casefold() == computer_name.strip().casefold()
        ]
        return max(matches, key=lambda request: (request.get("DateCreated", ""), request.get("Id", "")), default=None)

    def _save_requests(self, requests):
        self._write_text(self.requests_path, json.dumps(requests, indent=2))

    @staticmethod
    def _write_text(path, contents):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        try:
            temporary_path.write_text(contents, encoding="utf-8")
            temporary_path.replace(path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()


def export_request_pdf(request_text, output_path):
    lines = []
    for source_line in request_text.splitlines():
        wrapped = textwrap.wrap(source_line, width=88) or [""]
        lines.extend(line.encode("ascii", errors="replace").decode("ascii") for line in wrapped)

    text_commands = ["BT", "/F1 11 Tf", "50 750 Td", "14 TL"]
    for line in lines[:48]:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        text_commands.extend((f"({escaped}) Tj", "T*"))
    text_commands.append("ET")
    stream = "\n".join(text_commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n%TrustGate\n")
    offsets = [0]
    for index, content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii") + content + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf)