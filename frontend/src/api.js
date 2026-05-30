const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');

function appendDateFilters(params, filters = {}) {
  if (filters.start) params.set('start', `${filters.start}T00:00:00`);
  if (filters.end) params.set('end', `${filters.end}T23:59:59`);
  return params;
}

function buildLogQuery({ page = 1, pageSize = 20, filters = {} } = {}) {
  const params = appendDateFilters(new URLSearchParams(), filters);
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return params.toString();
}

export async function fetchLogs({ page = 1, pageSize = 20, filters = {} } = {}) {
  const response = await fetch(`${API_BASE}/logs?${buildLogQuery({ page, pageSize, filters })}`);
  if (!response.ok) throw new Error(`Failed to fetch logs: ${response.status}`);
  return response.json();
}

export async function fetchChartLogs(filters = {}) {
  const params = appendDateFilters(new URLSearchParams(), filters);
  params.set('limit', '10000');
  const response = await fetch(`${API_BASE}/logs/chart?${params.toString()}`);
  if (!response.ok) throw new Error(`Failed to fetch chart logs: ${response.status}`);
  return response.json();
}

export async function fetchModelUsage(filters = {}) {
  const params = appendDateFilters(new URLSearchParams(), filters);
  const query = params.toString();
  const response = await fetch(`${API_BASE}/models/usage${query ? `?${query}` : ''}`);
  if (!response.ok) throw new Error(`Failed to fetch model usage: ${response.status}`);
  return response.json();
}

export async function fetchStats(filters = {}) {
  const params = appendDateFilters(new URLSearchParams(), filters);
  const query = params.toString();
  const response = await fetch(`${API_BASE}/stats${query ? `?${query}` : ''}`);
  if (!response.ok) throw new Error(`Failed to fetch stats: ${response.status}`);
  return response.json();
}

export function buildLogsExportUrl(filters = {}) {
  const params = appendDateFilters(new URLSearchParams(), filters);
  const query = params.toString();
  return `${API_BASE}/logs/export${query ? `?${query}` : ''}`;
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
