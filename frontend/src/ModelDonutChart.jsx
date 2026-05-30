import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

const MODEL_COLORS = ['#0f766e', '#2563eb', '#7c3aed', '#e82127', '#b45309', '#334155', '#0891b2', '#be123c'];

export function formatTokens(value = 0) {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}

function colorForModel(modelName) {
  let hash = 0;
  for (const char of String(modelName || 'unknown-model')) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return MODEL_COLORS[hash % MODEL_COLORS.length];
}

function ModelTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="model-tooltip">
      <strong>{item.model_name}</strong>
      <span>{formatTokens(item.tokens)} tokens</span>
      <small>{item.request_count} 次请求 · {item.token_source === 'reported' ? '真实 Token' : '估算 Token'}</small>
    </div>
  );
}

export default function ModelDonutChart({ usage, compact = false }) {
  const items = usage?.items ?? [];
  const visibleItems = items.slice(0, 6);
  const totalTokens = usage?.total_tokens ?? visibleItems.reduce((sum, item) => sum + item.tokens, 0);

  return (
    <section className="card model-card">
      <div className="section-kicker">MODEL IDENTITY</div>
      <div className="card-title">大模型型号识别</div>
      {visibleItems.length === 0 ? (
        <div className="model-empty">暂无模型使用数据。新记录会根据上报模型名和 Token 自动统计。</div>
      ) : (
        <div className={`model-donut-layout ${compact ? 'compact' : ''}`}>
          <div className="donut-wrap">
            <ResponsiveContainer width="100%" height={compact ? 220 : 260}>
              <PieChart>
                <Pie data={visibleItems} dataKey="tokens" nameKey="model_name" innerRadius="62%" outerRadius="86%" paddingAngle={2} stroke="none">
                  {visibleItems.map((item, index) => (
                    <Cell key={item.model_name} fill={colorForModel(item.model_name)} />
                  ))}
                </Pie>
                <Tooltip content={<ModelTooltip />} wrapperStyle={{ zIndex: 20, pointerEvents: 'none' }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="donut-center">
              <strong>{formatTokens(totalTokens)}</strong>
              <span>tokens</span>
            </div>
          </div>
          <div className="model-legend-list">
            {visibleItems.map((item) => (
              <div className="model-legend-row" key={`${item.model_name}-${item.provider ?? 'none'}`}>
                <i style={{ background: colorForModel(item.model_name) }} aria-hidden="true" />
                <div>
                  <strong>{item.model_name}</strong>
                  <span>{formatTokens(item.tokens)} tokens · {item.request_count} 次</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
