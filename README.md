# TrustGate

## Employee Auto Login

The separate employee auto-login project is in [employee-auto-login](employee-auto-login/README.md). Its PowerShell scripts require Windows and PowerShell 5.1 or later; review its deployment and security documentation before use.

## TrustGate Setup

Install the runtime dependencies with `py -3 -m pip install -r requirements.txt`, then run `py -3 src/app.py`. To build a standalone Windows executable, run `powershell -ExecutionPolicy Bypass -File .\build.ps1`; the output is `dist\TrustGate.exe`. Copy this executable to a compatible Windows PC; it includes the Python runtime and the app's default configuration and printer template, so the source tree and Python are not required there. Windows Credential Manager must be available for secure credential features. Docker, WSL, and winget are optional separately installed integrations, not bundled dependencies.

Connection metadata is stored in `%LOCALAPPDATA%\TrustGate\settings.json`. API secrets, SSH private keys, and the per-install Ed25519 private identity key are stored in that Windows account's Credential Manager. Only the identity's public key is shown for registration with a platform. Profiles are saved locally; platform-specific network adapters must be implemented for the services you intend to use.

## Software Deployment

The Software Deployment page checks the configured Docker daemon, lists installed WSL distributions, and checks winget availability. Docker uses the current Docker context, which may point to a remote daemon. Select Windows Package Manager to install a package by its exact winget ID (for example, `Microsoft.PowerToys`); TrustGate asks for confirmation before running the installer from the configured `winget` source. The confirmation accepts package and source agreements. Installers may change the computer or request elevation, and should only be used with trusted package sources. These tools must already be installed and discoverable on `PATH`; TrustGate does not install them or deploy software through Docker or WSL.

## Dashboard and Plugin Marketplace

Select **Edit page** on the dashboard to add, remove, or reorder widgets using the dropdown. The **Plugin Marketplace** lists the built-in widgets and can add or remove them from the dashboard. Layouts are saved per Windows user in `%LOCALAPPDATA%\TrustGate\dashboard.json` (or `~/.local/share/TrustGate/dashboard.json` when `LOCALAPPDATA` is unavailable). The marketplace does not download or execute third-party plugins. These are local preferences, not department-wide layouts or administrator-enforced permissions; the other enterprise integrations and page-builder features in the plan are not yet implemented.

## Deployment UI Preview

The dashboard includes a preview-only AutoLogon Manager, company presets, computer-name validation, a deployment wizard, and local JSON preview-report export. Generic presets are bundled from `config/company_profiles.default.json`. To use private company settings, place a JSON file in `%LOCALAPPDATA%\TrustGate\company_profiles.json`; it takes precedence over the bundled presets. When running from source, an untracked `config/company_profiles.json` is also supported if no per-user file exists. Neither private file is included in the executable. The preview workflow does not change Windows AutoLogon settings, join a domain, reset directory passwords, rename the computer, or deploy software, printers, or drives. The separate Software Deployment page can install Windows packages as described above. AutoLogon passwords are not saved or included in audit events or reports.