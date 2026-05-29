const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');

export async function fetchLogs(limit = 100) {
  const response = await fetch(`${API_BASE}/logs?limit=${limit}`);
  if (!response.ok) throw new Error(`Failed to fetch logs: ${response.status}`);
  return response.json();
}

export async function fetchStats() {
  const response = await fetch(`${API_BASE}/stats`);
  if (!response.ok) throw new Error(`Failed to fetch stats: ${response.status}`);
  return response.json();
}

export async function fetchRelays() {
  const response = await fetch(`${API_BASE}/relays`);
  if (!response.ok) throw new Error(`加载中转站失败：${response.status}`);
  return response.json();
}

export async function saveRelay(relay) {
  const response = await fetch(`${API_BASE}/relays`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(relay),
  });
  if (!response.ok) throw new Error(`保存中转站失败：${response.status}`);
  return response.json();
}

export async function deleteRelay(name) {
  const response = await fetch(`${API_BASE}/relays/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(`删除中转站失败：${response.status}`);
  return response.json();
}

export async function ingestLog(payload) {
  const response = await fetch(`${API_BASE}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`上报分析失败：${response.status}`);
  return response.json();
}

export async function ask(prompt, relay = 'mock') {
  const response = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, relay }),
  });
  if (!response.ok) throw new Error(`Ask failed: ${response.status}`);
  return response.json();
}

export function connectLogStream(onMessage) {
  const socket = new WebSocket(`${WS_BASE}/ws/logs`);
  socket.onmessage = (event) => {
    onMessage(JSON.parse(event.data));
  };
  socket.onopen = () => socket.send('hello');
  return socket;
}

export { API_BASE };
