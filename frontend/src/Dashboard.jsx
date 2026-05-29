import { useEffect, useState } from 'react';
import { connectLogStream, fetchLogs, fetchStats } from './api.js';
import LogsTable from './LogsTable.jsx';
import RiskChart from './RiskChart.jsx';

const statusText = {
  connecting: '连接中',
  live: '监控中',
  'ws-error': '连接异常',
  offline: '已离线',
};

export default function Dashboard() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState('connecting');
  const [error, setError] = useState('');

  async function refresh() {
    const [nextLogs, nextStats] = await Promise.all([fetchLogs(), fetchStats()]);
    setLogs(nextLogs);
    setStats(nextStats);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
    const socket = connectLogStream((message) => {
      if (message.type === 'log') {
        setLogs((current) => [message.payload, ...current].slice(0, 100));
        fetchStats().then(setStats).catch(() => {});
      }
    });
    socket.onopen = () => {
      setStatus('live');
      socket.send('monitor-online');
    };
    socket.onerror = () => setStatus('ws-error');
    socket.onclose = () => setStatus('offline');
    return () => socket.close();
  }, []);

  const latest = logs[0];
  const latestRisk = latest?.analysis?.risk_label || '等待数据';
  const latestScore = latest?.analysis?.risk_score ?? 0;

  return (
    <main className="page simple-page">
      <header className="hero simple-hero">
        <div>
          <p className="eyebrow">LLM Monitor v8</p>
          <h1>Claude Code 后台监控</h1>
          <p className="subtitle">正常使用 Claude Code。系统后台读取本地日志，判断是否疑似混模型、漂移或降智。</p>
        </div>
        <div className={`status ${status}`}>{statusText[status] ?? status}</div>
      </header>

      <section className="card simple-card">
        <div className="card-title">怎么用</div>
        <ol className="simple-steps">
          <li>保持后端 / 前端窗口运行。</li>
          <li>保持监听脚本 <strong>watch-claude-logs.ps1</strong> 运行。</li>
          <li>照常使用 Claude Code 和 cc-switch。</li>
        </ol>
        <div className="safe-warning compact-warning">监控只读取本地 Claude Code 日志，不调用模型，不请求中转站，不产生额外 API 费用。</div>
        {error && <div className="error">连接提示：{error}</div>}
      </section>

      <section className="grid metrics-grid">
        <div className="metric"><span>监控条数</span><strong>{stats?.total ?? 0}</strong></div>
        <div className="metric"><span>高风险</span><strong>{stats?.high_risk ?? 0}</strong></div>
        <div className="metric"><span>最新状态</span><strong>{latestRisk}</strong></div>
        <div className="metric"><span>最新风险分</span><strong>{Number(latestScore).toFixed(3)}</strong></div>
      </section>

      <RiskChart logs={logs} />
      <LogsTable logs={logs} />
    </main>
  );
}
