$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    py -3 -m venv $Venv
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the build environment. Install Python 3.12 or later."
    }
}

& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Could not update pip in the build environment."
}

& $Python -m pip install -r (Join-Path $Root "requirements-build.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Could not install TrustGate build dependencies."
}

& $Python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name TrustGate `
    --distpath (Join-Path $Root "dist") `
    --workpath (Join-Path $Root "build") `
    --specpath $Root `
    --paths (Join-Path $Root "src") `
    --collect-all keyring `
    --collect-all cryptography `
    (Join-Path $Root "src\app.py")
if ($LASTEXITCODE -ne 0) {
    throw "TrustGate executable build failed."
}

Write-Output "Built: $(Join-Path $Root 'dist\TrustGate.exe')"