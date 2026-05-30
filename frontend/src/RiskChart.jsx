import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from 'recharts';
import { formatChartTick24, formatDateTime24, parseServerTime } from './time.js';

const riskStandards = [
  { label: '正常', range: '< 0.42', detail: '波动较小，未见明显降智信号', tone: 'ok' },
  { label: '注意', range: '0.42 - 0.72', detail: '风格或漂移偏高，建议观察', tone: 'warn' },
  { label: '疑似异常', range: '≥ 0.72', detail: '可能混入低质模型或明显降智', tone: 'danger' },
];

const driftStandards = [
  { label: '正常', range: '< 0.35', detail: '与近期语义和风格基线接近，漂移稳定', tone: 'ok' },
  { label: '注意', range: '0.35 - 0.65', detail: '表达风格或语义中心有抬升，建议持续观察', tone: 'warn' },
  { label: '疑似异常', range: '≥ 0.65', detail: '明显偏离近期基线，可能存在模型或质量波动', tone: 'danger' },
];

const severityLegend = [
  { label: '正常', range: '0 - 0.35', tone: 'ok' },
  { label: '注意', range: '0.35 - 0.65', tone: 'warn' },
  { label: '疑似异常', range: '0.65 - 0.72', tone: 'soft-danger' },
  { label: '高风险', range: '≥ 0.72', tone: 'danger' },
];

function severityColor(value) {
  if (value < 0.35) return '#166534';
  if (value < 0.65) return '#b45309';
  if (value < 0.72) return '#f87171';
  return '#b91c1c';
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload;
  const risk = Number(row?.risk ?? 0);
  const drift = Number(row?.drift ?? 0);

  return (
    <div className="chart-tooltip">
      <div className="tooltip-time">{row?.displayTime ?? label}</div>
      <div style={{ color: severityColor(drift) }}>漂移分：{drift.toFixed(4)}</div>
      <div style={{ color: severityColor(risk) }}>风险分：{risk.toFixed(4)}</div>
    </div>
  );
}

function StandardPanel({ kicker, title, standards, note, ariaLabel }) {
  return (
    <div className="standard-panel card" aria-label={ariaLabel}>
      <div className="section-kicker">{kicker}</div>
      <h3>{title}</h3>
      {standards.map((item) => (
        <div className={`standard-row ${item.tone}`} key={item.label}>
          <div>
            <strong>{item.label}</strong>
            <p>{item.detail}</p>
          </div>
          <span>{item.range}</span>
        </div>
      ))}
      <div className="standard-note">{note}</div>
    </div>
  );
}

export function StandardsRow() {
  return (
    <section className="standards-row" aria-label="评分标准">
      <StandardPanel
        kicker="RISK STANDARD"
        title="风险分标准"
        standards={riskStandards}
        note="风险分由本地漂移、异常检测、混模型概率和文本特征综合计算，不调用任何模型 API。"
        ariaLabel="风险分标准"
      />
      <StandardPanel
        kicker="DRIFT STANDARD"
        title="漂移分标准"
        standards={driftStandards}
        note="漂移分衡量当前回复相对近期本地语义 / 风格基线的偏离程度，数值越高表示偏离越明显。"
        ariaLabel="漂移分标准"
      />
    </section>
  );
}

export default function RiskChart({ logs, total }) {
  const data = [...logs]
    .sort((left, right) => parseServerTime(left.time) - parseServerTime(right.time))
    .map((log, index) => ({
      index: index + 1,
      time: log.time,
      displayTime: formatDateTime24(log.time),
      risk: log.analysis?.risk_score ?? 0,
      drift: log.analysis?.drift_score ?? 0,
      label: log.analysis?.risk_label ?? 'NA',
    }));

  const totalCount = total ?? data.length;

  return (
    <section className="card chart-card tesla-panel">
      <div className="chart-main">
        <div className="chart-header">
          <div>
            <div className="section-kicker">LIVE SIGNAL</div>
            <div className="card-title">后台监控趋势</div>
          </div>
          <div className="chart-meta">
            <div className="chart-count">已统计 {totalCount} 条，当前展示 {data.length} 个点</div>
            <div className="severity-legend" aria-label="危险程度颜色说明">
              {severityLegend.map((item) => (
                <span className={`severity-chip ${item.tone}`} key={item.label}>
                  <i aria-hidden="true" />
                  {item.label} {item.range}
                </span>
              ))}
            </div>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(92, 94, 98, 0.16)" />
            <XAxis
              dataKey="time"
              stroke="#5c5e62"
              tickLine={false}
              axisLine={false}
              minTickGap={28}
              tickFormatter={formatChartTick24}
            />
            <YAxis domain={[0, 1]} stroke="#5c5e62" tickLine={false} axisLine={false} />
            <Tooltip content={<ChartTooltip />} />
            <Line name="风险分" type="monotone" dataKey="risk" stroke="#b91c1c" strokeWidth={3} dot={false} connectNulls />
            <Line name="漂移分" type="monotone" dataKey="drift" stroke="#334155" strokeWidth={2} dot={false} opacity={0.82} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
