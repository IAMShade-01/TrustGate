# TrustGate

## Employee Auto Login

The separate employee auto-login project is in [employee-auto-login](employee-auto-login/README.md). Its PowerShell scripts require Windows and PowerShell 5.1 or later; review its deployment and security documentation before use.

## TrustGate Setup

Install the runtime dependencies with `py -3 -m pip install -r requirements.txt`, then run `py -3 src/app.py`. To build a standalone Windows executable, run `powershell -ExecutionPolicy Bypass -File .\build.ps1`; the output is `dist\TrustGate.exe`. The target PC does not need the source tree or Python installed.

Connection metadata is stored in `%LOCALAPPDATA%\TrustGate\settings.json`. API secrets, SSH private keys, and the per-install Ed25519 private identity key are stored in that Windows account's Credential Manager. Only the identity's public key is shown for registration with a platform. Profiles are saved locally; platform-specific network adapters must be implemented for the services you intend to use.