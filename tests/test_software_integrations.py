import subprocess
import unittest
from unittest.mock import patch

from software_integrations import (
    IntegrationError, check_status, install_package, validate_package_id,
)


class SoftwareIntegrationTests(unittest.TestCase):
    @patch("software_integrations.subprocess.run")
    @patch("software_integrations.shutil.which", return_value=r"C:\Tools\docker.exe")
    def test_docker_checks_daemon_without_shell(self, _which, run):
        run.return_value = subprocess.CompletedProcess([], 0, b"27.0.0\n", b"")
        self.assertIn("27.0.0", check_status("Docker Desktop"))
        args, kwargs = run.call_args
        self.assertEqual(args[0], [r"C:\Tools\docker.exe", "version", "--format", "{{.Server.Version}}"])
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["timeout"], 20)

    @patch("software_integrations.subprocess.run")
    @patch("software_integrations.shutil.which", return_value=r"C:\Windows\System32\wsl.exe")
    def test_wsl_decodes_windows_utf16_output(self, _which, run):
        run.return_value = subprocess.CompletedProcess([], 0, "Ubuntu\r\n".encode("utf-16-le"), b"")
        self.assertIn("Ubuntu", check_status("WSL"))
        self.assertEqual(run.call_args.args[0][1:], ["--list", "--quiet"])

    @patch("software_integrations.shutil.which", return_value=None)
    def test_missing_tool_is_reported(self, _which):
        with self.assertRaisesRegex(IntegrationError, "not found"):
            check_status("Windows Package Manager (winget)")

    @patch("software_integrations.subprocess.run")
    @patch("software_integrations.shutil.which", return_value=r"C:\Tools\docker.exe")
    def test_failed_connection_includes_error(self, _which, run):
        run.return_value = subprocess.CompletedProcess([], 1, b"", b"Daemon unavailable")
        with self.assertRaisesRegex(IntegrationError, "Daemon unavailable"):
            check_status("Docker Desktop")

    @patch("software_integrations.subprocess.run")
    def test_installs_exact_package_with_confirmed_executable(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, b"Installed", b"")
        result = install_package("Microsoft.PowerToys", r"C:\Tools\winget.exe")
        self.assertIn("Microsoft.PowerToys", result)
        self.assertEqual(
            run.call_args.args[0],
            [
                r"C:\Tools\winget.exe", "install", "--id", "Microsoft.PowerToys",
                "--exact", "--source", "winget", "--silent", "--disable-interactivity",
                "--accept-package-agreements", "--accept-source-agreements",
            ],
        )

    def test_rejects_invalid_package_ids(self):
        for package_id in ("", "--help", "Foo.Bar --force", "Foo;Bar", "Foo/Bar"):
            with self.subTest(package_id=package_id), self.assertRaises(IntegrationError):
                validate_package_id(package_id)

    @patch("software_integrations.subprocess.run")
    def test_timed_out_install_warns_installer_may_continue(self, run):
        run.side_effect = subprocess.TimeoutExpired("winget", 1800)
        with self.assertRaisesRegex(IntegrationError, "may still be running"):
            install_package("Microsoft.PowerToys", r"C:\Tools\winget.exe")


if __name__ == "__main__":
    unittest.main()
