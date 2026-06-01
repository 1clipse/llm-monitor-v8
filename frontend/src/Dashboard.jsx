import { useEffect, useMemo, useState } from 'react';
import { buildLogsExportUrl, connectLogStream, fetchChartLogs, fetchLogs, fetchModelUsage, fetchStats } from './api.js';
import LogsTable from './LogsTable.jsx';
import ModelDonutChart, { formatTokens } from './ModelDonutChart.jsx';
import { parseServerTime } from './time.js';
import RiskChart, { StandardsRow } from './RiskChart.jsx';

const statusText = {
  connecting: '连接中',
  live: '监控中',
  'ws-error': '连接异常',
  offline: '已离线',
};

const navItems = [
  { key: 'overview', label: '仪表盘', icon: '⌂' },
  { key: 'models', label: '模型识别', icon: '◌' },
  { key: 'risk', label: '风险漂移', icon: '⌁' },
  { key: 'logs', label: '监控记录', icon: '☰' },
  { key: 'integrations', label: '接入说明', icon: '↗' },
];

const defaultLogsPage = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  total_pages: 0,
  has_next: false,
  has_prev: false,
};

const quickRangeOptions = [
  { key: 'last6h', label: '近6小时', days: 1 },
  { key: 'yesterday', label: '昨天', type: 'yesterday' },
  { key: 'last24h', label: '近24小时', days: 1 },
  { key: 'last7d', label: '近 7 天', days: 7 },
  { key: 'last14d', label: '近 14 天', days: 14 },
  { key: 'last30d', label: '近 30 天', days: 30 },
  { key: 'thisMonth', label: '本月', type: 'thisMonth' },
  { key: 'lastMonth', label: '上月', type: 'lastMonth' },
];

function toDateInputValue(date) {
  const timezoneOffset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - timezoneOffset).toISOString().slice(0, 10);
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function getQuickRange(days) {
  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - days + 1);
  return {
    start: toDateInputValue(start),
    end: toDateInputValue(end),
  };
}

function getNamedRange(option) {
  const now = new Date();
  if (option.type === 'yesterday') {
    const yesterday = addDays(now, -1);
    return { start: toDateInputValue(yesterday), end: toDateInputValue(yesterday) };
  }
  if (option.type === 'thisMonth') {
    return { start: toDateInputValue(new Date(now.getFullYear(), now.getMonth(), 1)), end: toDateInputValue(now) };
  }
  if (option.type === 'lastMonth') {
    const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const end = new Date(now.getFullYear(), now.getMonth(), 0);
    return { start: toDateInputValue(start), end: toDateInputValue(end) };
  }
  return getQuickRange(option.days);
}

function formatDateLabel(value) {
  if (!value) return '未选择';
  return value.replaceAll('-', '/');
}

function getRangeLabel(filter) {
  const match = quickRangeOptions.find((option) => {
    const range = getNamedRange(option);
    return range.start === filter.start && range.end === filter.end;
  });
  if (match) return match.label;
  if (filter.start && filter.end) return `${formatDateLabel(filter.start)} - ${formatDateLabel(filter.end)}`;
  if (filter.start) return `${formatDateLabel(filter.start)} 之后`;
  if (filter.end) return `${formatDateLabel(filter.end)} 之前`;
  return '全部时间';
}

function inDateRange(log, filters) {
  const time = parseServerTime(log.time).getTime();
  if (Number.isNaN(time)) return false;

  if (filters.start) {
    const start = new Date(`${filters.start}T00:00:00`).getTime();
    if (time < start) return false;
  }

  if (filters.end) {
    const end = new Date(`${filters.end}T23:59:59`).getTime();
    if (time > end) return false;
  }

  return true;
}

function MetricCard({ label, value, hint }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </div>
  );
}

function CalendarIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7 3v3M17 3v3M4 9h16M6 5h12a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function AppShell({ activeScreen, onScreenChange, status, stats, modelUsage, children }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand"><span>LM</span><strong>LLM Monitor</strong></div>
        <nav className="sidebar-nav" aria-label="主功能导航">
          {navItems.map((item) => (
            <button type="button" className={`sidebar-nav-button ${activeScreen === item.key ? 'active' : ''}`} key={item.key} onClick={() => onScreenChange(item.key)}>
              <span>{item.icon}</span>{item.label}
            </button>
          ))}
        </nav>
      </aside>
      <div className="shell-main">
        <header className="top-status-bar">
          <div>
            <strong>{navItems.find((item) => item.key === activeScreen)?.label ?? '仪表盘'}</strong>
            <span>本地日志监控 · 漂移识别 · 模型用量分析</span>
          </div>
          <div className="top-status-actions">
            <span className={`status ${status}`}>{statusText[status] ?? status}</span>
            <span className="top-pill">{stats?.total ?? 0} 条</span>
            <span className="top-pill">{formatTokens(modelUsage?.total_tokens ?? 0)} Token</span>
          </div>
        </header>
        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}

function DateRangeToolbar({ dateFilter, selectedRangeKey, onApply, onRefresh, onReset, exportUrl }) {
  const [open, setOpen] = useState(false);
  const [draftFilter, setDraftFilter] = useState(dateFilter);
  const [draftRangeKey, setDraftRangeKey] = useState(selectedRangeKey);
  const rangeLabel = useMemo(() => getRangeLabel(dateFilter), [dateFilter]);

  function chooseQuickRange(option) {
    setDraftFilter(getNamedRange(option));
    setDraftRangeKey(option.key);
  }

  function applyDraft() {
    onApply(draftFilter, draftRangeKey);
    setOpen(false);
  }

  function togglePicker() {
    setDraftFilter(dateFilter);
    setDraftRangeKey(selectedRangeKey);
    setOpen((current) => !current);
  }

  return (
    <section className="card filter-card" aria-label="筛选和导出工具栏">
      <div className="filter-group">
        <label className="filter-field">
          <span>时间范围</span>
          <button type="button" className={`range-trigger ${open ? 'active' : ''}`} onClick={togglePicker} aria-expanded={open}>
            <CalendarIcon />
            <span>{rangeLabel}</span>
            <span className="chevron">⌄</span>
          </button>
        </label>

        {open && (
          <div className="range-popover" role="dialog" aria-label="选择导出和筛选日期范围">
            <div className="quick-range-panel">
              {quickRangeOptions.map((option) => {
                const active = draftRangeKey === option.key;
                return (
                  <button
                    type="button"
                    className={`quick-range-option ${active ? 'active' : ''}`}
                    key={option.key}
                    onClick={() => chooseQuickRange(option)}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
            <div className="range-input-panel">
              <label>
                开始日期
                <input type="date" value={draftFilter.start} onChange={(event) => { setDraftFilter((current) => ({ ...current, start: event.target.value })); setDraftRangeKey('custom'); }} />
              </label>
              <span className="range-arrow">→</span>
              <label>
                结束日期
                <input type="date" value={draftFilter.end} onChange={(event) => { setDraftFilter((current) => ({ ...current, end: event.target.value })); setDraftRangeKey('custom'); }} />
              </label>
            </div>
            <div className="range-popover-actions">
              <button type="button" className="secondary-button" onClick={() => setOpen(false)}>取消</button>
              <button type="button" className="apply-button" onClick={applyDraft}>应用</button>
            </div>
          </div>
        )}
      </div>

      <div className="filter-actions">
        <button type="button" className="secondary-button" onClick={onRefresh}>刷新</button>
        <button type="button" className="secondary-button" onClick={onReset}>重置</button>
        <a className="export-button" href={exportUrl}>导出 CSV</a>
      </div>
    </section>
  );
}

export default function Dashboard() {
  const [activeScreen, setActiveScreen] = useState('overview');
  const [logsPage, setLogsPage] = useState(defaultLogsPage);
  const [chartLogs, setChartLogs] = useState([]);
  const [modelUsage, setModelUsage] = useState(null);
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState('connecting');
  const [error, setError] = useState('');
  const [dateFilter, setDateFilter] = useState(getQuickRange(7));
  const [selectedRangeKey, setSelectedRangeKey] = useState('last7d');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [newRecordHint, setNewRecordHint] = useState(false);

  async function refresh(filters = dateFilter, nextPage = page, nextPageSize = pageSize) {
    const [nextLogsPage, nextChartLogs, nextModelUsage, nextStats] = await Promise.all([
      fetchLogs({ page: nextPage, pageSize: nextPageSize, filters }),
      fetchChartLogs(filters),
      fetchModelUsage(filters),
      fetchStats(filters),
    ]);
    setLogsPage(nextLogsPage);
    setChartLogs(nextChartLogs);
    setModelUsage(nextModelUsage);
    setStats(nextStats);
    setNewRecordHint(false);
  }

  function updateDateFilter(nextFilter, nextRangeKey = 'custom') {
    setPage(1);
    setSelectedRangeKey(nextRangeKey);
    setDateFilter(nextFilter);
  }

  function resetFilters() {
    updateDateFilter(getQuickRange(7), 'last7d');
  }

  function updatePageSize(nextPageSize) {
    setPage(1);
    setPageSize(nextPageSize);
  }

  useEffect(() => {
    refresh(dateFilter, page, pageSize).catch((err) => setError(err.message));
  }, [dateFilter, page, pageSize]);

  useEffect(() => {
    const socket = connectLogStream((message) => {
      if (message.type === 'log') {
        fetchStats(dateFilter).then(setStats).catch(() => {});
        fetchModelUsage(dateFilter).then(setModelUsage).catch(() => {});
        if (!inDateRange(message.payload, dateFilter)) return;
        fetchChartLogs(dateFilter).then(setChartLogs).catch(() => {});
        if (page === 1) {
          fetchLogs({ page: 1, pageSize, filters: dateFilter }).then(setLogsPage).catch(() => {});
        } else {
          setNewRecordHint(true);
        }
      }
    });
    socket.onopen = () => {
      setStatus('live');
      socket.send('monitor-online');
    };
    socket.onerror = () => setStatus('ws-error');
    socket.onclose = () => setStatus('offline');
    return () => socket.close();
  }, [dateFilter, page, pageSize]);

  const logs = logsPage.items ?? [];
  const latest = logs[0];
  const latestRisk = latest?.analysis?.risk_label || '等待数据';
  const latestScore = latest?.analysis?.risk_score ?? 0;
  const averageRisk = stats?.average_risk_score ?? 0;
  const averageDrift = stats?.average_drift_score ?? 0;
  const anomalyRatio = (stats?.anomaly_ratio ?? 0) * 100;
  const exportUrl = buildLogsExportUrl(dateFilter);

  const metrics = (
    <section className="grid metrics-grid">
      <MetricCard label="总对话数" value={stats?.total ?? 0} hint="筛选范围内" />
      <MetricCard label="高漂移对话数" value={stats?.high_drift ?? 0} hint="漂移 ≥ 0.65" />
      <MetricCard label="平均风险分" value={Number(averageRisk).toFixed(3)} hint="0 - 1" />
      <MetricCard label="平均漂移分" value={Number(averageDrift).toFixed(3)} hint="语义 / 风格" />
      <MetricCard label="提醒占比" value={`${anomalyRatio.toFixed(1)}%`} hint="需观察 + 建议复核" />
      <MetricCard label="最新状态" value={latestRisk} hint="当前页最新" />
      <MetricCard label="最新风险分" value={Number(latestScore).toFixed(3)} hint="当前页最新" />
    </section>
  );
  const toolbar = (
    <DateRangeToolbar
      dateFilter={dateFilter}
      selectedRangeKey={selectedRangeKey}
      onApply={updateDateFilter}
      onRefresh={() => refresh(dateFilter, page, pageSize).catch((err) => setError(err.message))}
      onReset={resetFilters}
      exportUrl={exportUrl}
    />
  );
  const logsTable = (
    <LogsTable
      logs={logs}
      pagination={logsPage}
      pageSize={pageSize}
      onPageChange={setPage}
      onPageSizeChange={updatePageSize}
      newRecordHint={newRecordHint}
      onShowLatest={() => setPage(1)}
    />
  );

  return (
    <AppShell activeScreen={activeScreen} onScreenChange={setActiveScreen} status={status} stats={stats} modelUsage={modelUsage}>
      {activeScreen === 'overview' && (
        <>
          <section className="screen-header"><p className="eyebrow">LLM Monitor v8</p><h1>Claude Code 后台监控</h1><p className="subtitle">正常使用 Claude Code。系统后台读取本地日志，给出漂移和复核提醒，不直接证明供应商或模型有问题。</p></section>
          {metrics}
          {toolbar}
          <section className="overview-grid"><RiskChart logs={chartLogs} total={stats?.total ?? chartLogs.length} /><ModelDonutChart usage={modelUsage} compact /></section>
        </>
      )}
      {activeScreen === 'models' && (
        <>
          {toolbar}
          <ModelDonutChart usage={modelUsage} />
        </>
      )}
      {activeScreen === 'risk' && (
        <>
          {toolbar}
          <RiskChart logs={chartLogs} total={stats?.total ?? chartLogs.length} />
          <StandardsRow />
        </>
      )}
      {activeScreen === 'logs' && (
        <>
          {toolbar}
          {logsTable}
        </>
      )}
      {activeScreen === 'integrations' && (
        <section className="card simple-card intro-card compact-intro-card">
          <div className="card-title">接入说明</div>
          <ol className="simple-steps">
            <li>保持后端 / 前端窗口运行。</li>
            <li>保持监听脚本 <strong>watch-claude-logs.ps1</strong> 运行。</li>
            <li>照常使用 Claude Code 和 cc-switch。</li>
          </ol>
          <div className="safe-warning compact-warning">监控只读取本地 Claude Code 日志，不调用模型，不请求中转站，不产生额外 API 费用。</div>
          {error && <div className="error">连接提示：{error}</div>}
        </section>
      )}
    </AppShell>
  );
}
