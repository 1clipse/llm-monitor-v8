$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Watcher = Join-Path $Root "scripts\watch-claude-logs.ps1"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  throw "Backend venv not found. Run .\scripts\setup.ps1 first."
}

$backendCommand = "Set-Location '$Backend'; & '$Python' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
$frontendCommand = "Set-Location '$Frontend'; npm run dev"
$watcherCommand = "Set-Location '$Root'; & '$Watcher'"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand
Start-Process powershell -ArgumentList "-NoExit", "-Command", $watcherCommand

"Started backend on http://localhost:8000, frontend on http://localhost:3000, and Claude Code log watcher"
