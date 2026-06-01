import { formatDateTime24 } from './time.js';

const riskText = {
  LOW: '正常',
  MEDIUM: '需观察',
  HIGH: '建议复核',
};

function riskClass(label) {
  return `risk-pill risk-${String(label || 'LOW').toLowerCase()}`;
}

function summary(text = '') {
  const compact = text.replace(/\s+/g, ' ').trim();
  return compact.length > 180 ? `${compact.slice(0, 180)}...` : compact;
}

function PaginationButton({ children, disabled, onClick, ariaLabel }) {
  return (
    <button type="button" className="pagination-button" disabled={disabled} onClick={onClick} aria-label={ariaLabel}>
      {children}
    </button>
  );
}

export default function LogsTable({
  logs,
  pagination,
  pageSize,
  onPageChange,
  onPageSizeChange,
  newRecordHint,
  onShowLatest,
}) {
  const total = pagination?.total ?? logs.length;
  const page = pagination?.page ?? 1;
  const totalPages = pagination?.total_pages ?? 0;
  const firstRow = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastRow = Math.min(page * pageSize, total);

  return (
    <section className="card table-card">
      <div className="table-toolbar">
        <div>
          <div className="section-kicker">LOGS</div>
          <div className="card-title">后台监控记录</div>
          <p>显示 {firstRow} 至 {lastRow}，共 {total} 条结果</p>
        </div>
        <div className="table-actions">
          {newRecordHint && (
            <button type="button" className="secondary-button" onClick={onShowLatest}>查看最新记录</button>
          )}
          <label className="page-size-control">
            每页
            <select value={pageSize} onChange={(event) => onPageSizeChange(Number(event.target.value))}>
              <option value="20">20</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </label>
        </div>
      </div>

      <div className="table-wrap">
        <table className="simple-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>Model</th>
              <th>状态</th>
              <th>风险分</th>
              <th>漂移</th>
              <th>回复摘要</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id ?? `${log.time}-${log.text}`}>
                <td>{formatDateTime24(log.time)}</td>
                <td className="model-cell">{log.model_name || 'unknown-model'}</td>
                <td><span className={riskClass(log.analysis?.risk_label)}>{riskText[log.analysis?.risk_label] ?? log.analysis?.risk_label}</span></td>
                <td>{Number(log.analysis?.risk_score ?? 0).toFixed(3)}</td>
                <td>{Number(log.analysis?.drift_score ?? 0).toFixed(3)}</td>
                <td className="summary-cell">{summary(log.text)}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan="6" className="empty">当前筛选范围暂无监控记录</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pagination-bar" aria-label="监控记录分页">
        <div className="pagination-summary">第 {totalPages === 0 ? 0 : page} / {totalPages} 页</div>
        <div className="pagination-controls">
          <PaginationButton disabled={!pagination?.has_prev} onClick={() => onPageChange(page - 1)} ariaLabel="上一页">‹</PaginationButton>
          <span>{page}</span>
          <PaginationButton disabled={!pagination?.has_next} onClick={() => onPageChange(page + 1)} ariaLabel="下一页">›</PaginationButton>
        </div>
      </div>
    </section>
  );
}
