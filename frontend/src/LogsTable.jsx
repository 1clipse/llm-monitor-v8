const riskText = {
  LOW: '正常',
  MEDIUM: '注意',
  HIGH: '疑似异常',
};

function riskClass(label) {
  return `risk-pill risk-${String(label || 'LOW').toLowerCase()}`;
}

function summary(text = '') {
  const compact = text.replace(/\s+/g, ' ').trim();
  return compact.length > 180 ? `${compact.slice(0, 180)}...` : compact;
}

export default function LogsTable({ logs }) {
  return (
    <section className="card table-card">
      <div className="card-title">后台监控记录</div>
      <div className="table-wrap">
        <table className="simple-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>状态</th>
              <th>风险分</th>
              <th>漂移</th>
              <th>回复摘要</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id ?? `${log.time}-${log.text}`}>
                <td>{new Date(log.time).toLocaleString()}</td>
                <td><span className={riskClass(log.analysis?.risk_label)}>{riskText[log.analysis?.risk_label] ?? log.analysis?.risk_label}</span></td>
                <td>{Number(log.analysis?.risk_score ?? 0).toFixed(3)}</td>
                <td>{Number(log.analysis?.drift_score ?? 0).toFixed(3)}</td>
                <td className="summary-cell">{summary(log.text)}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan="5" className="empty">等待 Claude Code 新回复...</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
