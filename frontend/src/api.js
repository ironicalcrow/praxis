const BASE = 'http://localhost:8000'

export function getToken() {
  return localStorage.getItem('praxis_token')
}

export function setToken(t) {
  localStorage.setItem('praxis_token', t)
}

export function clearToken() {
  localStorage.removeItem('praxis_token')
}

async function req(path, opts = {}) {
  const token = getToken()
  const headers = { ...(opts.headers || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (opts.json) {
    headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(opts.json)
    delete opts.json
  }
  const res = await fetch(`${BASE}${path}`, { ...opts, headers })
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`
    try { const d = await res.json(); msg = d.detail || JSON.stringify(d) } catch {}
    throw new Error(msg)
  }
  if (res.status === 204) return null
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('json')) return res.json()
  return res.text()
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const auth = {
  register: (d) => req('/api/auth/register', { method: 'POST', json: d }),
  login:    (d) => req('/api/auth/login', { method: 'POST', json: d }),
  logout:   ()  => req('/api/auth/logout', { method: 'POST' }),
  me:       ()  => req('/api/auth/me'),
}

// ── CV ────────────────────────────────────────────────────────────────────────
export const cv = {
  upload: (file) => {
    const fd = new FormData(); fd.append('file', file)
    return req('/api/cv/upload-cv', { method: 'POST', body: fd })
  },
  get:      ()  => req('/api/cv/my-cv'),
  uploads:  ()  => req('/api/cv/uploads'),
  activate: (id) => req(`/api/cv/uploads/${id}/activate`, { method: 'POST' }),
}

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const jobs = {
  search:      (d) => req('/api/jobs/live-search', { method: 'POST', json: d }),
  suggest:     ()  => req('/api/jobs/suggest-from-my-cv'),
  suggestNext: ()  => req('/api/jobs/suggest-from-my-cv/refresh', { method: 'POST' }),
  detail:      (id) => req(`/api/jobs/details/${id}`),
  status:      (id) => req(`/api/jobs/details/${id}/status`),
  queries:     ()  => req('/api/jobs/queries'),
  refreshQueries: () => req('/api/jobs/queries/refresh', { method: 'POST' }),
  prefs:       ()  => req('/api/jobs/preferences'),
  updatePrefs: (d)  => req('/api/jobs/preferences', { method: 'PUT', json: d }),
}

// ── Applications ──────────────────────────────────────────────────────────────
export const apps = {
  kanban:    (uid) => req(`/api/application/applications/kanban?user_id=${uid}`),
  list:      (uid, status) => req(`/api/application/applications?user_id=${uid}${status ? '&status=' + status : ''}`),
  fromJob:   (d)   => req('/api/application/applications/from-job', { method: 'POST', json: d }),
  manual:    (d)   => req('/api/application/applications/manual', { method: 'POST', json: d }),
  updateStatus: (id, d) => req(`/api/application/applications/${id}/status`, { method: 'PATCH', json: d }),
  addNote:   (id, d)   => req(`/api/application/applications/${id}/notes`, { method: 'POST', json: d }),
  updateNote:(id, d)   => req(`/api/application/notes/${id}`, { method: 'PATCH', json: d }),
  archive:   (id, uid) => req(`/api/application/applications/${id}/archive?user_id=${uid}`, { method: 'PATCH' }),
  delete:    (id, uid) => req(`/api/application/applications/${id}?user_id=${uid}`, { method: 'DELETE' }),
}

// ── Chat ──────────────────────────────────────────────────────────────────────
export const chat = {
  send:        (d) => req('/api/chat/message', { method: 'POST', json: d }),
  sendJob:     (jobId, d) => req(`/api/chat/job/${jobId}/message`, { method: 'POST', json: d }),
  history:     (limit = 20) => req(`/api/chat/history?limit=${limit}`),
  historyJob:  (jobId, limit = 20) => req(`/api/chat/job/${jobId}/history?limit=${limit}`),
  sessions:    () => req('/api/chat/sessions'),
  sessionsJob: (jobId) => req(`/api/chat/job/${jobId}/sessions`),
}

// ── Cover Letters ─────────────────────────────────────────────────────────────
export const coverLetters = {
  generate: (d)   => req('/api/cover-letter/generate', { method: 'POST', json: d }),
  list:     ()    => req('/api/cover-letter/'),
  get:      (id)  => req(`/api/cover-letter/${id}`),
  update:   (id, d) => req(`/api/cover-letter/${id}`, { method: 'PATCH', json: d }),
  delete:   (id)  => req(`/api/cover-letter/${id}`, { method: 'DELETE' }),
}

// ── Roadmaps ──────────────────────────────────────────────────────────────────
export const roadmaps = {
  fromConversation: (d) => req('/api/roadmap/from-conversation', { method: 'POST', json: d }),
  fromJob:  (d)   => req('/api/roadmap/from-job', { method: 'POST', json: d }),
  manual:   (d)   => req('/api/roadmap/manual', { method: 'POST', json: d }),
  list:     ()    => req('/api/roadmap/'),
  get:      (id)  => req(`/api/roadmap/${id}`),
  delete:   (id)  => req(`/api/roadmap/${id}`, { method: 'DELETE' }),
}

// ── Goals ─────────────────────────────────────────────────────────────────────
export const goals = {
  create:     (d)  => req('/api/goals/', { method: 'POST', json: d }),
  fromRoadmap:(id, d) => req(`/api/goals/from-roadmap/${id}`, { method: 'POST', json: d || {} }),
  list:       (status) => req(`/api/goals/${status ? '?status=' + status : ''}`),
  get:        (id) => req(`/api/goals/${id}`),
  update:     (id, d) => req(`/api/goals/${id}`, { method: 'PATCH', json: d }),
  delete:     (id) => req(`/api/goals/${id}`, { method: 'DELETE' }),
}

// ── Notifications ─────────────────────────────────────────────────────────────
export const notifications = {
  list:       (unreadOnly) => req(`/api/notifications/${unreadOnly ? '?unread_only=true' : ''}`),
  markRead:   (id) => req(`/api/notifications/${id}/read`, { method: 'PATCH' }),
  markAllRead: () => req('/api/notifications/mark-all-read', { method: 'POST' }),
  delete:     (id) => req(`/api/notifications/${id}`, { method: 'DELETE' }),
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
export function createNotificationWS(onMessage, onOpen, onClose) {
  const token = getToken()
  const ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${token}`)
  ws.onmessage = (e) => { try { onMessage(JSON.parse(e.data)) } catch {} }
  ws.onopen = onOpen
  ws.onclose = onClose
  return ws
}

// ── Health ────────────────────────────────────────────────────────────────────
export const health = () => fetch(`${BASE}/health`).then(r => r.json())
