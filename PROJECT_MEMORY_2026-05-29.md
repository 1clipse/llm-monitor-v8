---
name: llm-monitor-v8-session-2026-05-29
description: 2026-05-29 LLM Monitor v8 项目完整会话记忆，存放在 D 盘项目内
metadata:
  type: project
  date: 2026-05-29
---

# LLM Monitor v8 项目会话记忆 — 2026-05-29

## 用户核心目标

用户要在 `D:\LLMtext` 下做一个本地 LLM 监控系统，用来在自己正常使用 Claude Code / cc-switch 调模型时，后台实时监控模型回复是否疑似：

- 混入低质量模型
- 降智
- 风格漂移
- 异常输出
- 风险升高

关键要求：

- 监控本身不能调用任何模型 API。
- 监控本身不能产生任何额外费用。
- 用户不想复杂操作，不想复杂网页。
- 用户正常使用 Claude Code 即可，系统后台监控。
- 所有依赖和环境尽量放在 D 盘项目目录内。
- 后续记忆也要求保存在 D 盘，不要存在 C 盘。

## 已创建项目

项目目录：

```text
D:\LLMtext\llm-monitor-v8
```

主要结构：

```text
llm-monitor-v8/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── router.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── analyzer.py
│   │   ├── embedder.py
│   │   ├── anomaly.py
│   │   ├── cluster.py
│   │   ├── client.py
│   │   ├── metrics.py
│   │   ├── websocket.py
│   │   ├── auth.py
│   │   └── notifier.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── Dashboard.jsx
│   │   ├── RiskChart.jsx
│   │   ├── LogsTable.jsx
│   │   ├── ProbabilityMap.jsx
│   │   ├── RelaySettings.jsx
│   │   ├── IngestPanel.jsx
│   │   ├── api.js
│   │   └── styles.css
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   ├── setup.ps1
│   ├── run-dev.ps1
│   └── watch-claude-logs.ps1
├── data/
│   ├── relays.json
│   ├── logs.json
│   └── claude-log-watcher-state.json
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## 环境与依赖

用户已执行：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\setup.ps1
```

安装成功：

- Python 虚拟环境：`D:\LLMtext\llm-monitor-v8\backend\.venv`
- 前端依赖：`D:\LLMtext\llm-monitor-v8\frontend\node_modules`

## 启动方式

### 启动前后端

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\run-dev.ps1
```

会打开：

- 后端：`http://localhost:8000`
- 前端：`http://localhost:3000`

### 启动后台监听器

另开一个 PowerShell：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\watch-claude-logs.ps1
```

监听器读取：

```text
C:\Users\Knightz\.claude\projects\**\*.jsonl
```

然后把新 assistant 文本回复上报给本地：

```text
http://127.0.0.1:8000/ingest
```

## 用户实际模型工具情况

用户开始说的是 `ccswitch`，但检查后发现：

```powershell
ccswitch --help
```

不可用。

后来确认实际运行的是：

```text
D:\cc-switch.exe
```

进程名：

```text
cc-switch
```

配置和数据位置：

```text
C:\Users\Knightz\.cc-switch\settings.json
C:\Users\Knightz\.cc-switch\logs\cc-switch.log
C:\Users\Knightz\.cc-switch\cc-switch.db
```

cc-switch 数据库中发现表：

```text
proxy_request_logs
model_pricing
providers
provider_endpoints
proxy_config
session_log_sync
stream_check_logs
usage_daily_rollups
```

`proxy_request_logs` 有模型、token、成本、延迟等元数据，但没有完整回复文本。

`session_log_sync` 指向 Claude Code JSONL 会话文件，例如：

```text
C:\Users\Knightz\.claude\projects\d--LLMtext\6f79b85e-b0b2-4572-a01a-324508498330.jsonl
```

所以最终采用的方案是：监听 Claude Code JSONL，而不是直接监听 cc-switch 数据库。

## 零费用监控方案

最终方案：

```text
Claude Code 正常工作
↓
cc-switch 正常代理模型调用
↓
Claude Code 把回复写入本地 JSONL 日志
↓
watch-claude-logs.ps1 读取新 assistant 回复
↓
POST 到本地 /ingest
↓
LLM Monitor 本地分析
↓
Dashboard 实时显示
```

费用边界：

- `watch-claude-logs.ps1` 只读本地日志。
- `/ingest` 只分析已生成文本。
- 不调用 OpenAI、Claude、中转站或 cc-switch API。
- 不产生额外模型费用。

## 后端接口

### `/ingest`

零费用被动上报接口。

请求格式：

```json
{
  "relay": "cc-switch/claude-code",
  "model": "cc-switch-observed",
  "prompt": "",
  "text": "assistant reply text",
  "metadata": {
    "source": "claude-jsonl-watcher",
    "file": "...",
    "uuid": "...",
    "timestamp": "...",
    "session_id": "..."
  }
}
```

### `/ask`

主动测试接口，可能调用中转站；用户最终不想使用它作为主流程。

### `/integrations/cc-connect`

曾为 cc-connect hook 添加过适配接口，但用户实际用的是 cc-switch，因此不是主路径。

## 风险评分规则

风险分范围：

```text
0.000 ~ 1.000
```

默认阈值在 `backend/app/config.py`：

```python
risk_medium_threshold = 0.42
risk_high_threshold = 0.72
```

前端显示：

| 风险分 | 状态 |
|---:|---|
| `< 0.42` | 正常 |
| `0.42 - 0.72` | 注意 |
| `>= 0.72` | 疑似异常 |

计算规则在 `backend/app/analyzer.py`：

- 异常检测命中：`+0.38`
- 漂移分大于 0.35：最高 `+0.32`
- 混模型概率分布不集中：`+0.18`
- 回复长度超过 4000 字符：`+0.08`
- 包含 error / exception / traceback / failed：`+0.08`
- 最终封顶 1.0

重要说明：这是本地行为检测和预警，不是供应商内部路由证明。

## 前端演变

最初前端包含：

- 手动 `/ingest` 表单
- 中转站设置
- API Key 编辑
- 主动 `/ask` 测试
- 模型概率地图
- 风险曲线
- 日志表格

用户觉得太复杂，要求简化成后台监控。

最终前端保留：

- Claude Code 后台监控标题
- 监控条数
- 高风险
- 最新状态
- 最新风险分
- 后台监控趋势
- 后台监控记录

去掉了复杂配置入口。

## Tesla 风格 UI

用户要求：

- 用 `ui-ux-pro-max` skill
- 风格参考特斯拉官网
- 把风险分标准加到曲线图右侧

使用 `ui-ux-pro-max` 搜索得到建议：

- Minimal Single Column
- Dark Mode / OLED
- 高对比
- 大字号
- 大留白
- 黑白红配色
- 红色作为风险强调色

已修改：

- `frontend/src/RiskChart.jsx`
- `frontend/src/styles.css`

曲线图右侧加入：

```text
风险分标准
正常        < 0.42
注意        0.42 - 0.72
疑似异常    ≥ 0.72
```

## 乱码问题

用户发现前端“回复摘要”出现 `????`。

原因：Windows PowerShell 5.1 用字符串 body 发送 JSON 时可能不是 UTF-8，中文变问号。

已修复 `scripts/watch-claude-logs.ps1`：

```powershell
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($json)
Invoke-RestMethod -ContentType "application/json; charset=utf-8" -Body $bodyBytes
```

旧乱码已经写入 SQLite，无法自动恢复；如不需要历史记录，可删除：

```powershell
Remove-Item D:\LLMtext\llm-monitor-v8\data\llm_monitor.db
```

然后重启后端。

## 422 问题

监听器曾报：

```text
Monitor post failed: 远程服务器返回错误: (422) Unprocessable Entity
```

原因推测：Claude Code 某些回复太长，超过 `/ingest` 的 `text` 最大长度限制 `200000`。

已修复 `scripts/watch-claude-logs.ps1`：

- 自动截断到约 190000 字符
- 追加提示 `[watcher: reply truncated before local analysis]`
- 捕获错误时输出后端详细响应

## 当前推荐工作流

用户最终只需要：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\run-dev.ps1
```

另开窗口：

```powershell
cd D:\LLMtext\llm-monitor-v8
.\scripts\watch-claude-logs.ps1
```

然后正常使用 Claude Code / cc-switch。

网页：

```text
http://localhost:3000
```

## 验证记录

多次运行通过：

```powershell
cd D:\LLMtext\llm-monitor-v8\frontend
npm run build
```

通过但有 Vite chunk 体积警告，不影响运行。

后端编译多次通过：

```powershell
cd D:\LLMtext\llm-monitor-v8\backend
.\.venv\Scripts\python -m compileall app
```

监听脚本语法检查通过：

```powershell
$null = [scriptblock]::Create((Get-Content "D:\LLMtext\llm-monitor-v8\scripts\watch-claude-logs.ps1" -Raw)); 'OK'
```

## 用户偏好

- 用户希望中文沟通。
- 用户希望简单直接，不要复杂说明。
- 用户不想网页复杂。
- 用户不希望再把记忆存在 C 盘。
- 用户明确取消了 Git 版本管理和远程推送，不用继续 Git。

## 后续注意事项

- 如果用户说网页复杂，继续简化，不要加配置入口。
- 如果用户问费用，强调：监控脚本只读本地日志，`/ingest` 只本地分析，不调用 API。
- 如果用户发现乱码，确认监听脚本是否已重启；旧数据库记录无法恢复。
- 如果用户发现没有监控新回复，确认顺序：先启动监听器，再让 Claude Code 产生新回复。
- 如果用户想清空历史，删除 `data/llm_monitor.db` 后重启后端。
- 不要再主动推进 Git；用户已说不用 Git。
