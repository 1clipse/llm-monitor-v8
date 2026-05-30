export function parseServerTime(value) {
  if (!value) return new Date(Number.NaN);
  if (value instanceof Date) return value;
  const text = String(value);
  if (/([zZ]|[+-]\d{2}:?\d{2})$/.test(text)) return new Date(text);
  return new Date(`${text}Z`);
}

export function formatDateTime24(value, options = {}) {
  const date = parseServerTime(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString('zh-CN', {
    hour12: false,
    year: options.year ?? 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: options.second ?? '2-digit',
  });
}

export function formatChartTick24(value) {
  const date = parseServerTime(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', {
    hour12: false,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}
