import locale
import re
import shutil
import subprocess


INTEGRATIONS = ("Docker Desktop", "WSL", "Windows Package Manager (winget)")
PACKAGE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,255}\Z")


class IntegrationError(RuntimeError):
    pass


def executable_path(name):
    path = shutil.which(name)
    if not path:
        raise IntegrationError(f"{name} was not found. Install it and make sure it is on PATH.")
    return path


def validate_package_id(package_id):
    package_id = package_id.strip()
    if not PACKAGE_ID.fullmatch(package_id):
        raise IntegrationError("Enter an exact winget package ID, such as Microsoft.PowerToys.")
    return package_id


def _decode_output(data):
    if not data:
        return ""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    if b"\x00" in data:
        return data.decode("utf-16-le", errors="replace")
    return data.decode(locale.getpreferredencoding(False), errors="replace")


def _run(executable, arguments, timeout):
    try:
        result = subprocess.run(
            [executable, *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as error:
        message = "The command timed out."
        if arguments and arguments[0] == "install":
            message += " An installer started by winget may still be running; check Windows before retrying."
        raise IntegrationError(message) from error
    except OSError as error:
        raise IntegrationError(f"Could not run {executable}: {error}") from error

    output = "\n".join(
        text for text in (_decode_output(result.stdout).strip(), _decode_output(result.stderr).strip())
        if text
    )
    if result.returncode:
        raise IntegrationError(
            f"Command failed (exit code {result.returncode})."
            + (f"\n{output}" if output else "")
        )
    return output


def check_status(integration):
    if integration == "Docker Desktop":
        executable = executable_path("docker.exe")
        output = _run(executable, ["version", "--format", "{{.Server.Version}}"], 20)
        return f"Docker daemon reachable. Server version: {output or 'not reported'}"
    if integration == "WSL":
        executable = executable_path("wsl.exe")
        output = _run(executable, ["--list", "--quiet"], 20)
        return f"WSL is available. Installed distributions:\n{output}" if output else (
            "WSL is available, but no distributions were listed."
        )
    if integration == "Windows Package Manager (winget)":
        executable = executable_path("winget.exe")
        output = _run(executable, ["--version"], 20)
        return f"winget is available. Version: {output or 'not reported'}"
    raise IntegrationError(f"Unsupported integration: {integration}")


def install_package(package_id, executable):
    package_id = validate_package_id(package_id)
    output = _run(
        executable,
        [
            "install", "--id", package_id, "--exact", "--source", "winget",
            "--silent", "--disable-interactivity", "--accept-package-agreements",
            "--accept-source-agreements",
        ],
        1800,
    )
    return f"winget completed installation of {package_id}." + (f"\n\n{output}" if output else "")
