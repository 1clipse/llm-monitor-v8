import { useEffect, useMemo, useState } from 'react';
import { deleteRelay, fetchRelays, saveRelay } from './api.js';

const emptyRelay = {
  name: '',
  type: 'openai_compatible',
  url: '',
  model: '',
  api_key: '',
  api_key_env: '',
};

export default function RelaySettings({ selectedRelay, onSelectedRelayChange }) {
  const [relays, setRelays] = useState([]);
  const [form, setForm] = useState(emptyRelay);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  async function loadRelays() {
    const nextRelays = await fetchRelays();
    setRelays(nextRelays);
    if (!selectedRelay && nextRelays[0]) {
      onSelectedRelayChange(nextRelays[0].name);
    }
  }

  useEffect(() => {
    loadRelays().catch((err) => setMessage(`加载失败：${err.message}`));
  }, []);

  const currentRelay = useMemo(() => {
    return relays.find((relay) => relay.name === selectedRelay) || relays[0];
  }, [relays, selectedRelay]);

  function editRelay(relay) {
    setForm({
      name: relay.name || '',
      type: relay.type || 'openai_compatible',
      url: relay.url || '',
      model: relay.model || '',
      api_key: relay.api_key || '',
      api_key_env: relay.api_key_env || '',
    });
  }

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submitRelay(event) {
    event.preventDefault();
    setLoading(true);
    setMessage('');
    try {
      const saved = await saveRelay(form);
      await loadRelays();
      onSelectedRelayChange(saved.name);
      setForm({ ...saved, api_key: saved.api_key || '' });
      setMessage('中转站已保存。');
    } catch (err) {
      setMessage(`保存失败：${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function removeRelay() {
    if (!form.name || form.name === 'mock') return;
    setLoading(true);
    setMessage('');
    try {
      await deleteRelay(form.name);
      setForm(emptyRelay);
      onSelectedRelayChange('mock');
      await loadRelays();
      setMessage('中转站已删除。');
    } catch (err) {
      setMessage(`删除失败：${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card relay-card">
      <div className="card-title">中转站设置</div>
      <div className="relay-warning">
        混模型检测、漂移分析、风险评分都在本地完成，不会额外调用付费 API；只有点击“发送并分析”且选择真实中转站时，才会产生一次中转站调用。
      </div>

      <div className="relay-toolbar">
        <label>
          当前发送中转站
          <select value={selectedRelay || currentRelay?.name || 'mock'} onChange={(event) => onSelectedRelayChange(event.target.value)}>
            {relays.map((relay) => (
              <option key={relay.name} value={relay.name}>{relay.name}</option>
            ))}
          </select>
        </label>
        <button type="button" className="secondary-button" onClick={() => setForm(emptyRelay)}>新增中转站</button>
      </div>

      <form onSubmit={submitRelay} className="relay-form">
        <div className="form-grid">
          <label>
            中转站名称
            <input value={form.name} onChange={(event) => updateField('name', event.target.value)} placeholder="例如 my-relay" required />
          </label>
          <label>
            模型名称
            <input value={form.model} onChange={(event) => updateField('model', event.target.value)} placeholder="例如 gpt-4o-mini" />
          </label>
          <label className="wide-field">
            接口地址
            <input value={form.url} onChange={(event) => updateField('url', event.target.value)} placeholder="https://你的中转站/v1/chat/completions" />
          </label>
          <label>
            API Key
            <input value={form.api_key} onChange={(event) => updateField('api_key', event.target.value)} placeholder="sk-... 或保留 ******** 不变" type="password" />
          </label>
          <label>
            API Key 环境变量名（可选）
            <input value={form.api_key_env} onChange={(event) => updateField('api_key_env', event.target.value)} placeholder="例如 MY_RELAY_API_KEY" />
          </label>
        </div>

        <div className="relay-actions">
          <button disabled={loading || form.name === 'mock'}>{loading ? '保存中...' : '保存中转站'}</button>
          <button type="button" className="danger-button" disabled={loading || !form.name || form.name === 'mock'} onClick={removeRelay}>删除</button>
        </div>
      </form>

      <div className="relay-list">
        {relays.map((relay) => (
          <button key={relay.name} type="button" className="relay-chip" onClick={() => editRelay(relay)}>
            {relay.name} · {relay.model || relay.type}
          </button>
        ))}
      </div>
      {message && <div className="relay-message">{message}</div>}
    </section>
  );
}
