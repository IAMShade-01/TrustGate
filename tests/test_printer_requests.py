import json
import tempfile
import unittest
from pathlib import Path

from printer_requests import PrinterRequestError, PrinterRequestStore, export_request_pdf


class PrinterRequestStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.store = PrinterRequestStore(
            requests_path=root / "printer_requests.json",
            template_path=root / "printer_request_template.txt",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def request_fields(self):
        return {
            "computer_name": "DEVICE01",
            "user_name": "jsmith",
            "location": "Example Location",
            "department": "Example Department",
            "printer_type": "Zebra Label Printer",
            "printer_team_contact": "printerteam@company.com",
            "reason": "New workstation deployment.",
            "requested_by": "Example User",
            "requested_by_title": "Infrastructure Engineer",
        }

    def test_create_and_update_request_persists_status(self):
        request = self.store.create_request(self.request_fields())
        updated = self.store.update_status(request["Id"], "Complete")

        saved = json.loads(self.store.requests_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["Status"], "Complete")
        self.assertEqual(saved[0]["ComputerName"], "DEVICE01")
        self.assertEqual(saved[0]["RequestType"], "Printer")
        self.assertEqual(self.store.latest_for_computer("device01")["Status"], "Complete")

    def test_custom_template_is_saved_and_used(self):
        self.store.save_template("Ticket for {computer_name}: {printer_type}")
        request = self.store.create_request(self.request_fields())

        self.assertEqual(request["RequestText"], "Ticket for DEVICE01: Zebra Label Printer")

    def test_missing_fields_and_unknown_template_fields_are_rejected(self):
        with self.assertRaises(PrinterRequestError):
            self.store.create_request({})
        with self.assertRaises(PrinterRequestError):
            self.store.save_template("Unknown {field}")
            self.store.create_request(self.request_fields())

    def test_pdf_export_writes_a_pdf_document(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "request.pdf"
            export_request_pdf("PRINTER REQUEST\nComputer: DEVICE01", output_path)

            contents = output_path.read_bytes()
        self.assertTrue(contents.startswith(b"%PDF-1.4"))
        self.assertTrue(contents.rstrip().endswith(b"%%EOF"))


if __name__ == "__main__":
    unittest.main()