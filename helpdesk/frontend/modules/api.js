const API = (window.API_BASE_URL || 'http://localhost:8000') + '/api/v1';

const _token = () => localStorage.getItem('helpdesk_token');

const _headers = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${_token()}`,
});

async function _fetch(url, options = {}) {
  const res = await fetch(url, { ...options, headers: _headers() });
  if (res.status === 401) {
    localStorage.removeItem('helpdesk_token');
    window.location.href = '/login.html';
    return;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Auth ────────────────────────────────────────────────────────────────────

export const AuthAPI = {
  login: (email, password) =>
    _fetch(`${API}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: () => _fetch(`${API}/auth/me`),
  refresh: () => _fetch(`${API}/auth/refresh`, { method: 'POST' }),
};

// ── Tickets ─────────────────────────────────────────────────────────────────

export const TicketAPI = {
  list: (params = {}) =>
    _fetch(`${API}/tickets?${new URLSearchParams(params)}`),

  get: (id) => _fetch(`${API}/tickets/${id}`),

  create: (data) =>
    _fetch(`${API}/tickets`, { method: 'POST', body: JSON.stringify(data) }),

  update: (id, data) =>
    _fetch(`${API}/tickets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  cancel: (id) =>
    _fetch(`${API}/tickets/${id}`, { method: 'DELETE' }),

  escalate: (id, nivel, reason) =>
    _fetch(`${API}/tickets/${id}/escalate`, {
      method: 'POST',
      body: JSON.stringify({ nivel, reason }),
    }),

  assign: (id, analyst_id) =>
    _fetch(`${API}/tickets/${id}/assign`, {
      method: 'POST',
      body: JSON.stringify({ analyst_id }),
    }),

  comment: (id, note, type = 'comment') =>
    _fetch(`${API}/tickets/${id}/comment`, {
      method: 'POST',
      body: JSON.stringify({ note, type }),
    }),

  resolve: (id, note) =>
    _fetch(`${API}/tickets/${id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),

  changePriority: (id, priority, reason) =>
    _fetch(`${API}/tickets/${id}/change-priority`, {
      method: 'POST',
      body: JSON.stringify({ priority, reason }),
    }),
};

// ── AI ──────────────────────────────────────────────────────────────────────

export const AIAPI = {
  analyze: (data) =>
    _fetch(`${API}/ai/analyze`, { method: 'POST', body: JSON.stringify(data) }),

  suggest: (ticketId) =>
    _fetch(`${API}/ai/suggest/${ticketId}`, { method: 'POST' }),
};

// ── Users ────────────────────────────────────────────────────────────────────

export const UserAPI = {
  list: (params = {}) => _fetch(`${API}/users?${new URLSearchParams(params)}`),
  get: (id) => _fetch(`${API}/users/${id}`),
  create: (data) => _fetch(`${API}/users`, { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => _fetch(`${API}/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => _fetch(`${API}/users/${id}`, { method: 'DELETE' }),
};

// ── Analysts ─────────────────────────────────────────────────────────────────

export const AnalystAPI = {
  list: (params = {}) => _fetch(`${API}/analysts?${new URLSearchParams(params)}`),
  get: (id) => _fetch(`${API}/analysts/${id}`),
  create: (data) => _fetch(`${API}/analysts`, { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => _fetch(`${API}/analysts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => _fetch(`${API}/analysts/${id}`, { method: 'DELETE' }),
};

// ── Departments ───────────────────────────────────────────────────────────────

export const DeptAPI = {
  list: () => _fetch(`${API}/departments`),
  create: (data) => _fetch(`${API}/departments`, { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => _fetch(`${API}/departments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => _fetch(`${API}/departments/${id}`, { method: 'DELETE' }),
};

// ── Categories ────────────────────────────────────────────────────────────────

export const CategoryAPI = {
  list: () => _fetch(`${API}/categories`),
  create: (data) => _fetch(`${API}/categories`, { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => _fetch(`${API}/categories/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => _fetch(`${API}/categories/${id}`, { method: 'DELETE' }),
};

// ── SLA ───────────────────────────────────────────────────────────────────────

export const SLAAPI = {
  rules: () => _fetch(`${API}/sla/rules`),
  updateRule: (priority, data) =>
    _fetch(`${API}/sla/rules/${priority}`, { method: 'PUT', body: JSON.stringify(data) }),
  breaches: () => _fetch(`${API}/sla/breaches`),
  atRisk: () => _fetch(`${API}/sla/at-risk`),
};

// ── Reports ───────────────────────────────────────────────────────────────────

export const ReportAPI = {
  kpis: (start, end) => {
    const params = {};
    if (start) params.start = start;
    if (end) params.end = end;
    return _fetch(`${API}/reports/kpis?${new URLSearchParams(params)}`);
  },
  byCategory: () => _fetch(`${API}/reports/by-category`),
  byAnalyst: () => _fetch(`${API}/reports/by-analyst`),
  byPriority: () => _fetch(`${API}/reports/by-priority`),
  slaPerformance: (start, end) => {
    const params = {};
    if (start) params.start = start;
    if (end) params.end = end;
    return _fetch(`${API}/reports/sla-performance?${new URLSearchParams(params)}`);
  },
  escalation: () => _fetch(`${API}/reports/escalation`),
  resolutionTime: () => _fetch(`${API}/reports/resolution-time`),
  exportCsv: async () => {
    const res = await fetch(`${API}/reports/export?format=csv`, { headers: _headers() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chamados_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  },
};
