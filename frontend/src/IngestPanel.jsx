import { useState } from 'react';
import { ingestLog } from './api.js';

const pythonExample = `import requests

# 你的程序正常调用模型并拿到结果之后：
requests.post("http://localhost:8000/ingest", json={
    "relay": "my-current-relay",
    "model": "gpt-4o-mini",
    "prompt": user_prompt,
    "text": model_response_text,
    "metadata": {"request_id": "abc123"}
})`;

const watcherExample = `# 推荐：cc-switch + Claude Code 零费用实时监听
# 先启动 LLM Monitor，再新开一个 PowerShell 运行：

cd D:\\LLMtext\\llm-monitor-v8
.\\scripts\\watch-claude-logs.ps1

# 然后正常使用 Claude Code / cc-switch。
# 监听脚本只读取本地 .claude/projects/*.jsonl 日志，
# 不请求模型、不请求中转站、不产生 API 费用。`;

export default function IngestPanel({ onIngested }) {
  const [form, setForm] = useState({
    relay: 'external',
    model: '',
    prompt: '用户原始提示词',
    text: '把你已经拿到的模型回复粘贴到这里，用于本地分析。',
  });
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submitIngest(event) {
    event.preventDefault();
    if (!form.text.trim()) return;
    setSubmitting(true);
    setMessage('');
    try {
      const log = await ingestLog({
        relay: form.relay || 'external',
        model: form.model || undefined,
        prompt: form.prompt || '',
        text: form.text,
        metadata: { source: 'dashboard-manual-ingest' },
      });
      setMessage(`已本地分析：${log.analysis.risk_label}，风险分 ${log.analysis.risk_score}`);
      onIngested?.(log);
    } catch (err) {
      setMessage(`上报失败：${err.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card ingest-card">
      <div className="card-title">零费用实时监控接入</div>
      <div className="safe-warning">
        推荐使用此模式：运行监听脚本读取 Claude Code 本地 JSONL 会话日志，把已经得到的助手回复上报到 <strong>/ingest</strong>。本系统只做本地分析，不请求模型、不请求中转站、不产生额外 API 费用。
      </div>

      <form className="ingest-form" onSubmit={submitIngest}>
        <div className="form-grid">
          <label>
            来源 / 中转站名称
            <input value={form.relay} onChange={(event) => updateField('relay', event.target.value)} placeholder="例如 my-relay" />
          </label>
          <label>
            模型名称
            <input value={form.model} onChange={(event) => updateField('model', event.target.value)} placeholder="例如 gpt-4o-mini" />
          </label>
          <label className="wide-field">
            原始提示词
            <textarea value={form.prompt} onChange={(event) => updateField('prompt', event.target.value)} />
          </label>
          <label className="wide-field">
            已获得的模型回复
            <textarea value={form.text} onChange={(event) => updateField('text', event.target.value)} />
          </label>
        </div>
        <button disabled={submitting}>{submitting ? '本地分析中...' : '上报并分析（不调用模型 API）'}</button>
        {message && <div className="relay-message">{message}</div>}
      </form>

      <details className="integration-examples">
        <summary>查看接入代码示例</summary>
        <p>cc-switch / Claude Code 监听脚本：</p>
        <pre>{watcherExample}</pre>
        <p>Python 手动上报示例：</p>
        <pre>{pythonExample}</pre>
      </details>
    </section>
  );
}
