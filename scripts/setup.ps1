$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Venv = Join-Path $Backend ".venv"

if (-not (Test-Path $Venv)) {
  python -m venv $Venv
}

& (Join-Path $Venv "Scripts\python.exe") -m pip install --upgrade pip
& (Join-Path $Venv "Scripts\python.exe") -m pip install -r (Join-Path $Backend "requirements.txt")

Push-Location $Frontend
try {
  npm install
}
finally {
  Pop-Location
}

Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env") -ErrorAction SilentlyContinue

"Setup complete. Backend venv: $Venv; frontend dependencies: $(Join-Path $Frontend 'node_modules')"
