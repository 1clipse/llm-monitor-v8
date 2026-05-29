import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from 'recharts';

const standards = [
  { label: '正常', range: '< 0.42', detail: '波动较小，未见明显降智信号', tone: 'ok' },
  { label: '注意', range: '0.42 - 0.72', detail: '风格或漂移偏高，建议观察', tone: 'warn' },
  { label: '疑似异常', range: '≥ 0.72', detail: '可能混入低质模型或明显降智', tone: 'danger' },
];

export default function RiskChart({ logs }) {
  const data = [...logs]
    .reverse()
    .slice(-50)
    .map((log, index) => ({
      index: index + 1,
      risk: log.analysis?.risk_score ?? 0,
      drift: log.analysis?.drift_score ?? 0,
      label: log.analysis?.risk_label ?? 'NA',
    }));

  return (
    <section className="card chart-card tesla-panel">
      <div className="chart-layout">
        <div className="chart-main">
          <div className="section-kicker">LIVE SIGNAL</div>
          <div className="card-title">后台监控趋势</div>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.16)" />
              <XAxis dataKey="index" stroke="#94a3b8" tickLine={false} axisLine={false} />
              <YAxis domain={[0, 1]} stroke="#94a3b8" tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: '#050505', border: '1px solid rgba(255,255,255,.16)', borderRadius: 12 }} />
              <ReferenceLine y={0.42} stroke="#f59e0b" strokeDasharray="4 4" />
              <ReferenceLine y={0.72} stroke="#dc2626" strokeDasharray="4 4" />
              <Line name="风险分" type="monotone" dataKey="risk" stroke="#dc2626" strokeWidth={3} dot={false} />
              <Line name="漂移分" type="monotone" dataKey="drift" stroke="#e5e7eb" strokeWidth={2} dot={false} opacity={0.75} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <aside className="risk-standard" aria-label="风险分标准">
          <div className="section-kicker">RISK STANDARD</div>
          <h3>风险分标准</h3>
          {standards.map((item) => (
            <div className={`standard-row ${item.tone}`} key={item.label}>
              <div>
                <strong>{item.label}</strong>
                <p>{item.detail}</p>
              </div>
              <span>{item.range}</span>
            </div>
          ))}
          <div className="standard-note">风险分由本地漂移、异常检测、混模型概率和文本特征综合计算，不调用任何模型 API。</div>
        </aside>
      </div>
    </section>
  );
}
