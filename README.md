# LLM Monitor v8

**作者:** Kimziyi

工业级本地优先的 LLM 监控面板，基于 FastAPI + React + WebSocket 实时更新 + Prometheus 指标 + SQLite/PostgreSQL 双存储，支持混合模型检测、漂移分析和风险评分。

## v8.2 更新说明

本版本重点优化风控判定流程，降低 DeepSeek / GPT-5.5 等官方 API 正常回复的误报，并让面板文案更符合“本地启发式提醒”的定位：

- 风险分析支持按 `provider:model` / `model` / `relay` 建立独立本地基线，避免不同供应商和模型互相污染历史样本。
- `/ask`、`/ingest` 和 `cc-connect` 集成会把已有的 relay、provider、model、session 等上下文传入分析器。
- 新增 `context_key`、`baseline_size`、`baseline_status`、`confidence` 和结构化 `signals`，方便判断当前提醒是否有足够基线支撑。
- 冷启动和 warming 阶段不再轻易触发统计型高风险；`mixed_model` 只有在基线 ready 且漂移升高时才会触发。
- 错误关键词判定区分普通说明和 hard failure / stack trace，减少正常技术回答中的误报。
- 前端将“异常 / 高风险”文案调整为“需观察 / 建议复核”，强调本地监控不能直接证明供应商或模型有问题。
- 新增 DeepSeek、GPT-5.5、基线隔离和 hard failure 的回归测试。

## v8.1 更新说明

本版本重点强化 Claude Code 后台监控、模型用量识别和大屏可用性：

- `run-dev.ps1` 现在会同时启动后端、前端和 Claude Code JSONL 监听器，减少漏开 watcher 导致的不更新问题。
- Claude Code 监听器会读取真实 `message.model` 和 token usage，上报到 `/ingest` 后在面板展示模型名、Token、Provider 和来源。
- 监听器状态文件改为 UTF-8 原子写入；状态损坏时会自动备份并重建，避免实时采集静默失效。
- 新增模型用量接口 `/models/usage`、分页日志 `/logs`、趋势日志 `/logs/chart` 和 CSV 导出 `/logs/export`。
- 前端新增模型 Token 环图、日期范围筛选、分页日志、风险 / 漂移标准说明和 24 小时时间显示。
- 新增 Claude JSONL 历史回填脚本，可把已有记录补齐模型名和 token 信息。

## 模型支持

面板现已完整支持多模型识别与用量统计：

- **模型识别**：自动从 Claude Code JSONL 中读取 `message.model`，识别每次调用的具体模型（如 `claude-opus-4-8`、`claude-sonnet-4-6` 等）
- **Token 统计**：记录每次调用的 `input_tokens` 和 `output_tokens`，按模型聚合展示
- **Provider 识别**：自动标记模型来源 Provider
- **模型用量仪表盘**：前端提供模型 Token 环图（`/models/usage`），直观展示各模型用量占比
- **日志表模型列**：监控日志表格中显示每条记录的模型名
- **历史回填**：提供 `backfill_models_from_claude_logs.py` 脚本，可为已有 JSONL 记录补齐模型名和 token 信息

## 功能特性

- FastAPI 后端，提供 `/ask`、`/ingest`、`/logs`、`/stats`、`/health`、`/metrics`、`/models/usage` 接口
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

只需运行：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\run-dev.ps1
```

脚本会自动打开三个窗口：FastAPI 后端、Vite 前端和 Claude Code JSONL 监听器。之后正常使用 Claude Code 即可。打开面板：

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

原理：`cc-switch` 将请求元数据存储在 `C:\Users\Knightz\.cc-switch\cc-switch.db`，但实际的助手回复文本、模型名和 token usage 保存在 `C:\Users\Knightz\.claude\projects` 下的 Claude Code 会话日志中。监控器读取这些本地 JSONL 文件，仅将已生成的助手回复 POST 到 `/ingest`。

运行顺序：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\run-dev.ps1
```

`run-dev.ps1` 会自动启动 `watch-claude-logs.ps1`。如果你只想单独启动监听器，也可以另开 PowerShell 手动运行：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\watch-claude-logs.ps1
```

之后正常使用 Claude Code / cc-switch 即可。新的助手回复文本将被分析并显示在面板上，并统计模型名、Token、Provider 和风险 / 漂移信息。

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

状态文件默认写入：

```text
data/claude-log-watcher-state.json
```

如果状态文件损坏，监听器会自动备份为 `*.bad-yyyyMMdd-HHmmss` 并从新状态继续运行。首次遇到新 JSONL 文件时会从文件末尾开始监听，避免重放旧会话；如需补齐历史模型名和 token，可运行：

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\backfill_models_from_claude_logs.py
```

## 模型用量、筛选与导出

面板现在支持：

- 按模型聚合 Token 和请求次数，显示模型 Token 环图。
- 按日期范围筛选仪表盘、趋势图、日志表和模型用量。
- 后台监控记录分页查看。
- 风险分 / 漂移分标准说明。
- 导出当前筛选范围内的 CSV：`GET /logs/export`。

相关接口：

```text
GET /logs?page=1&page_size=20
GET /logs/chart?limit=10000
GET /models/usage
GET /stats
GET /logs/export
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
