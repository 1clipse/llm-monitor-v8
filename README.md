# LLM Monitor v8

**Author:** Kimziyi

Industrial local-first LLM monitoring dashboard with FastAPI, React, WebSocket live updates, Prometheus metrics, SQLite/PostgreSQL-compatible storage, mixed-model detection, drift analysis, and risk scoring.

## Features

- FastAPI backend with `/ask`, `/ingest`, `/logs`, `/stats`, `/health`, `/metrics`
- WebSocket stream at `/ws/logs`
- Prometheus metrics via `prometheus-client`
- SQLite by default; PostgreSQL can be enabled with `DATABASE_URL`
- Multi-relay client with a built-in mock relay and OpenAI-compatible relay support
- Lightweight local embedding features, IsolationForest/SVM anomaly checks, KMeans-style model probability map, drift scoring, risk labels
- React + Vite dashboard with live logs, risk curve, drift curve, model probability map
- Docker Compose one-command deployment
- Windows scripts that keep Python venv and npm dependencies under this project directory

## Recommended simple use

This project is intended to run quietly in the background while you use Claude Code normally through cc-switch.

Run only these two commands:

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\run-dev.ps1
```

Then open a second PowerShell:

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\watch-claude-logs.ps1
```

After that, use Claude Code normally. Open the simple dashboard at:

```text
http://localhost:3000
```

The monitor only reads local Claude Code JSONL logs and sends already-generated assistant replies to the local `/ingest` endpoint. It does not call models, relays, OpenAI, Claude, or cc-switch APIs. Monitoring adds zero model API cost.

## Directory

```text
backend/      FastAPI service
frontend/     React dashboard
data/         local SQLite db, relay config, uploaded files
scripts/      Windows setup/run scripts
```

## Local setup on Windows

From `D:\LLMtext\llm-monitor-v8`:

```powershell
.\scripts\setup.ps1
.\scripts\run-dev.ps1
```

The setup script creates:

- `backend/.venv`
- `frontend/node_modules`

Both stay inside `D:\LLMtext\llm-monitor-v8`.

## Manual development commands

Backend:

```powershell
cd D:\LLMtext\llm-monitor-v8\backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd D:\LLMtext\llm-monitor-v8\frontend
npm run dev
```

Open:

- Dashboard: http://localhost:3000
- API docs: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics

## Zero-cost realtime monitoring mode

Use `POST /ingest` when you want this system to monitor model calls made by your own program without adding any paid API calls.

Flow:

```text
your app calls your model normally
↓
your app receives the model response
↓
your app posts prompt + response text to http://localhost:8000/ingest
↓
LLM Monitor v8 analyzes locally and updates the dashboard in realtime
```

`/ingest` never calls a model, relay, OpenAI, Claude, or any paid API. It only analyzes text you already received.

Python example:

```python
import requests

# after your normal model call finishes:
requests.post("http://localhost:8000/ingest", json={
    "relay": "my-current-relay",
    "model": "gpt-4o-mini",
    "prompt": user_prompt,
    "text": model_response_text,
    "metadata": {"request_id": "abc123"}
})
```

PowerShell example:

```powershell
Invoke-RestMethod http://localhost:8000/ingest `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"relay":"my-relay","model":"gpt-4o-mini","prompt":"你好","text":"模型已经返回的内容"}'
```

Cost boundary:

- `/ingest`: zero model API cost; local analysis only.
- `/ask`: active test call; it may call the selected relay and can cost money if that relay is paid.
- `mock`: local fake relay; no external call and no cost.

## API smoke test

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ask -Method Post -ContentType "application/json" -Body '{"prompt":"Test the monitor","relay":"mock"}'
Invoke-RestMethod http://localhost:8000/logs
```

## Docker

```powershell
cd D:\LLMtext\llm-monitor-v8
docker compose up --build
```

Then open http://localhost:3000.

## Relay configuration

Edit `data/relays.json` to add OpenAI-compatible relays:

```json
{
  "name": "my-relay",
  "type": "openai_compatible",
  "url": "https://your-relay/v1/chat/completions",
  "api_key_env": "MY_RELAY_KEY",
  "model": "your-model"
}
```

Set the matching environment variable in `.env` or your shell.

## cc-switch / Claude Code realtime watcher

For this Windows setup, the recommended zero-cost monitoring mode is the Claude Code JSONL watcher.

Why: `cc-switch` stores request metadata in `C:\Users\Knightz\.cc-switch\cc-switch.db`, but the actual assistant reply text is available in Claude Code session logs under `C:\Users\Knightz\.claude\projects`. The watcher reads those local JSONL files and posts only already-generated assistant replies to `/ingest`.

Run order:

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\run-dev.ps1
```

Then open another PowerShell:

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\watch-claude-logs.ps1
```

Then continue using Claude Code / cc-switch normally. New assistant text replies will be analyzed and shown on the dashboard.

Cost guarantee:

- The watcher only reads local `*.jsonl` files.
- The watcher only posts already-generated reply text to `http://127.0.0.1:8000/ingest`.
- It never calls cc-switch, a relay, OpenAI, Claude, or any paid model API.
- Monitoring adds no model API cost.

Watcher options:

```powershell
.\scripts\watch-claude-logs.ps1 `
  -ProjectsDir "C:\Users\Knightz\.claude\projects" `
  -MonitorUrl "http://127.0.0.1:8000/ingest" `
  -PollSeconds 2
```

## cc-connect hook integration

Your `cc-connect config example` shows support for HTTP hooks. To monitor cc-connect replies in realtime, edit:

```text
C:\Users\Knightz\.cc-connect\config.toml
```

Add this block at top-level, outside any `[[projects]]` block:

```toml
[[hooks]]
event = "message.sent"
type = "http"
url = "http://127.0.0.1:8000/integrations/cc-connect"
async = true
timeout = 5
```

Then restart cc-connect:

```powershell
cc-connect daemon restart
```

If you run cc-connect in the foreground, stop it and start it again.

This hook sends completed cc-connect replies to LLM Monitor. LLM Monitor only analyzes the received text locally. It does not call any model API.

Manual adapter test:

```powershell
Invoke-RestMethod http://localhost:8000/integrations/cc-connect `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"event":"message.sent","message":{"text":"这是 cc-connect 发出的模型回复"},"project":"my-backend"}'
```

## Storage

Default local database:

```text
data/llm_monitor.db
```

To use PostgreSQL, set `DATABASE_URL`, for example:

```env
DATABASE_URL=postgresql+psycopg2://llm_monitor:llm_monitor@localhost:5432/llm_monitor
```

## Verification

```powershell
cd D:\LLMtext\llm-monitor-v8\backend
.\.venv\Scripts\python -m compileall app
.\.venv\Scripts\python -m pytest

cd D:\LLMtext\llm-monitor-v8\frontend
npm run build
```
