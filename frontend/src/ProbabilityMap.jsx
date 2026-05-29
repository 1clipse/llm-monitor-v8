const modelNameText = {
  gpt_like: 'GPT 风格',
  claude_like: 'Claude 风格',
  local_or_mixed: '本地 / 混合风格',
};

export default function ProbabilityMap({ probabilities = {} }) {
  const entries = Object.entries(probabilities);

  return (
    <section className="card">
      <div className="card-title">实时模型概率地图</div>
      <div className="probability-list">
        {entries.length === 0 && <div className="muted">暂无模型概率数据。</div>}
        {entries.map(([name, value]) => (
          <div className="probability-row" key={name}>
            <div className="probability-header">
              <span>{modelNameText[name] ?? name}</span>
              <strong>{Math.round(value * 100)}%</strong>
            </div>
            <div className="bar-shell">
              <div className="bar-fill" style={{ width: `${Math.max(2, value * 100)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
