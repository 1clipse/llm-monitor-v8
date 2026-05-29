# LLM Monitor v8

**作者:** Kimziyi

工业级本地优先的 LLM 监控面板，基于 FastAPI + React + WebSocket 实时更新 + Prometheus 指标 + SQLite/PostgreSQL 双存储，支持混合模型检测、漂移分析和风险评分。

## 功能特性

- FastAPI 后端，提供 `/ask`、`/ingest`、`/logs`、`/stats`、`/health`、`/metrics` 接口
- WebSocket 实时推送 `/ws/logs`
- 通过 `prometheus-client` 暴露 Prometheus 指标
- 默认 SQLite 存储，可通过 `DATABASE_URL` 切换至 PostgreSQL
- 多中继客户端，内置 mock 中继和 OpenAI 兼容中继支持
- 轻量级本地向量特征提取、IsolationForest/SVM 异常检测、KMeans 风格模型概率图、漂移评分、风险标签
- React + Vite 面板，包含实时日志、风险曲线、漂移曲线、模型概率图
- Docker Compose 一键部署
- Windows 脚本，Python venv 和 npm 依赖均放在项目目录内

## 推荐用法

本项目设计为你正常使用 Claude Code（通过 cc-switch）时在后台静默运行。

只需在两个 PowerShell 窗口中分别运行：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\run-dev.ps1
```

第二个 PowerShell：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\watch-claude-logs.ps1
```

之后正常使用 Claude Code 即可。打开面板：

```text
http://localhost:3000
```

监控器仅读取本地 Claude Code JSONL 日志，将已生成的助手回复发送到本地 `/ingest` 接口。它不会调用任何模型、中继、OpenAI、Claude 或 cc-switch API。监控过程零模型 API 费用。

## 目录结构

```text
backend/      FastAPI 服务端
frontend/     React 面板
data/         本地 SQLite 数据库、中继配置、上传文件
scripts/      Windows 安装/运行脚本
```

## Windows 本地安装

在 `D:\LLMtext\llm-monitor-v8` 下执行：

```powershell
.\scripts\setup.ps1
.\scripts\run-dev.ps1
```

安装脚本会创建：

- `backend/.venv`
- `frontend/node_modules`

两者均在 `D:\LLMtext\llm-monitor-v8` 目录内。

## 手动开发命令

后端：

```powershell
cd D:\LLMtext\llm-monitor-v8\backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```powershell
cd D:\LLMtext\llm-monitor-v8\frontend
npm run dev
```

打开：

- 面板: http://localhost:3000
- API 文档: http://localhost:8000/docs
- 指标: http://localhost:8000/metrics

## 零成本实时监控模式

如果你想用自己的程序监控模型调用，且不希望产生任何额外的付费 API 调用，请使用 `POST /ingest`。

流程：

```text
你的应用正常调用模型
↓
你的应用收到模型回复
↓
你的应用将 prompt + 回复文本 POST 到 http://localhost:8000/ingest
↓
LLM Monitor v8 在本地分析并实时更新面板
```

`/ingest` 绝不调用任何模型、中继、OpenAI、Claude 或付费 API，仅分析你已经收到的文本。

Python 示例：

```python
import requests

# 正常模型调用完成后：
requests.post("http://localhost:8000/ingest", json={
    "relay": "my-current-relay",
    "model": "gpt-4o-mini",
    "prompt": user_prompt,
    "text": model_response_text,
    "metadata": {"request_id": "abc123"}
})
```

PowerShell 示例：

```powershell
Invoke-RestMethod http://localhost:8000/ingest `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"relay":"my-relay","model":"gpt-4o-mini","prompt":"你好","text":"模型已经返回的内容"}'
```

费用边界：

- `/ingest`：零模型 API 费用，仅本地分析。
- `/ask`：主动测试调用，可能会调用选定的中继，如果该中继是付费的则会产生费用。
- `mock`：本地假中继，无外部调用，零费用。

## API 冒烟测试

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ask -Method Post -ContentType "application/json" -Body '{"prompt":"测试监控器","relay":"mock"}'
Invoke-RestMethod http://localhost:8000/logs
```

## Docker 部署

```powershell
cd D:\LLMtext\llm-monitor-v8
docker compose up --build
```

然后打开 http://localhost:3000。

## 中继配置

编辑 `data/relays.json` 添加 OpenAI 兼容中继：

```json
{
  "name": "my-relay",
  "type": "openai_compatible",
  "url": "https://your-relay/v1/chat/completions",
  "api_key_env": "MY_RELAY_KEY",
  "model": "your-model"
}
```

在 `.env` 或终端环境变量中设置对应的 API Key。

## cc-switch / Claude Code 实时监控

在此 Windows 环境下，推荐使用零成本的 Claude Code JSONL 监控模式。

原理：`cc-switch` 将请求元数据存储在 `C:\Users\Knightz\.cc-switch\cc-switch.db`，但实际的助手回复文本保存在 `C:\Users\Knightz\.claude\projects` 下的 Claude Code 会话日志中。监控器读取这些本地 JSONL 文件，仅将已生成的助手回复 POST 到 `/ingest`。

运行顺序：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\run-dev.ps1
```

然后打开另一个 PowerShell：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\watch-claude-logs.ps1
```

之后正常使用 Claude Code / cc-switch 即可。新的助手回复文本将被分析并显示在面板上。

费用保证：

- 监控器仅读取本地 `*.jsonl` 文件。
- 监控器仅将已生成的回复文本 POST 到 `http://127.0.0.1:8000/ingest`。
- 绝不调用 cc-switch、任何中继、OpenAI、Claude 或任何付费模型 API。
- 监控过程零模型 API 费用。

监控器参数：

```powershell
.\scripts\watch-claude-logs.ps1 `
  -ProjectsDir "C:\Users\Knightz\.claude\projects" `
  -MonitorUrl "http://127.0.0.1:8000/ingest" `
  -PollSeconds 2
```

## cc-connect 钩子集成

`cc-connect config example` 支持 HTTP 钩子。要实时监控 cc-connect 回复，编辑：

```text
C:\Users\Knightz\.cc-connect\config.toml
```

在顶层（任意 `[[projects]]` 块之外）添加以下配置：

```toml
[[hooks]]
event = "message.sent"
type = "http"
url = "http://127.0.0.1:8000/integrations/cc-connect"
async = true
timeout = 5
```

然后重启 cc-connect：

```powershell
cc-connect daemon restart
```

如果你以前台方式运行 cc-connect，请先停止再重新启动。

此钩子将 cc-connect 完成的回复发送到 LLM Monitor。LLM Monitor 仅在本地分析收到的文本，不调用任何模型 API。

手动适配器测试：

```powershell
Invoke-RestMethod http://localhost:8000/integrations/cc-connect `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"event":"message.sent","message":{"text":"这是 cc-connect 发出的模型回复"},"project":"my-backend"}'
```

## 存储

默认本地数据库：

```text
data/llm_monitor.db
```

使用 PostgreSQL 时，设置 `DATABASE_URL`，例如：

```env
DATABASE_URL=postgresql+psycopg2://llm_monitor:llm_monitor@localhost:5432/llm_monitor
```

## 验证

```powershell
cd D:\LLMtext\llm-monitor-v8\backend
.\.venv\Scripts\python -m compileall app
.\.venv\Scripts\python -m pytest

cd D:\LLMtext\llm-monitor-v8\frontend
npm run build
```
