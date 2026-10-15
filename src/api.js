const JSON_HEADERS = { 'Content-Type': 'application/json' }

// Admin "test live mode": the server answers with fake live scores (backend/demo.py). Only admins get them.
let demoLive = (() => { try { return localStorage.getItem('demoLive') === 'on' } catch { return false } })()
export const isDemoLive = () => demoLive
export function setDemoLive(on) {
  demoLive = on
  try { localStorage.setItem('demoLive', on ? 'on' : 'off') } catch {}
}

async function call(url, opts = {}) {
  if (demoLive) opts = { ...opts, headers: { ...opts.headers, 'X-Demo-Live': '1' } }
  const r = await fetch(url, opts)
  if (!r.ok) {
    const body = await r.json().catch(() => ({}))
    if (r.status === 401 && !url.startsWith('/api/auth/')) window.dispatchEvent(new Event('pool:logged-out'))
    throw new Error(typeof body.detail === 'string' ? body.detail : r.statusText)
  }
  return r.json()
}
const send = (method, url, body) => call(url, { method, headers: JSON_HEADERS, body: JSON.stringify(body) })

export const getMe = () => call('/api/auth/me')
export const login = (username, password) => send('POST', '/api/auth/login', { username, password })
export const getSignupInfo = () => call('/api/auth/signup')
export const signup = body => send('POST', '/api/auth/signup', body)
export const logout = () => send('POST', '/api/auth/logout', {})
export const changePassword = (current, next) => send('POST', '/api/auth/password', { current, new: next })

export const getLines = week => call(`/api/lines${week ? `?week=${week}` : ''}`)
export const getDeadlines = week => call(`/api/deadlines${week ? `?week=${week}` : ''}`)
export const getAnnouncement = () => call('/api/announcement')
export const getWeeks = () => call('/api/weeks')
export const getWeek = n => call(`/api/weeks/${n}`)
export const saveWeek = (n, body) => send('PUT', `/api/weeks/${n}`, body)
export const deleteWeek = n => call(`/api/weeks/${n}`, { method: 'DELETE' })
export const uploadImage = (n, file) => call(`/api/weeks/${n}/image`, { method: 'PUT', headers: { 'Content-Type': file.type }, body: file })
export const getStats = () => call('/api/stats')
export const getPlayers = () => call('/api/players')
export const getPlayerWeeks = id => call(`/api/players/${id}/weeks`)
export const getPlayerWeek = (id, n) => call(`/api/players/${id}/weeks/${n}`)
export const getPlayerStats = id => call(`/api/players/${id}/stats`)
export const getWeekStandings = n => call(`/api/standings/week/${n}`)
export const getSeasonStandings = () => call('/api/standings/season')
export const getPool = n => call(`/api/weeks/${n}/pool`)
export const getSplits = n => call(`/api/splits?week=${n}`)
export const getTeamCovers = beforeWeek => call(`/api/teams?before_week=${beforeWeek}`)

export const admin = {
  users: () => call('/api/admin/users'),
  createUser: body => send('POST', '/api/admin/users', body),
  updateUser: (id, body) => send('PATCH', `/api/admin/users/${id}`, body),
  deleteUser: id => call(`/api/admin/users/${id}`, { method: 'DELETE' }),
  week: n => call(`/api/admin/weeks/${n}`),
  setDeadlines: (n, overrides) => send('PUT', `/api/admin/weeks/${n}/deadlines`, { overrides }),
  setPick: (userId, n, body) => send('PATCH', `/api/admin/picks/${userId}/${n}`, body),
  deleteLines: n => call(`/api/admin/weeks/${n}/lines`, { method: 'DELETE' }),
  signup: () => call('/api/admin/signup'),
  setSignup: body => send('PUT', '/api/admin/signup', body),
  setAnnouncement: text => send('PUT', '/api/admin/announcement', { text }),
  restore: file => call('/api/admin/restore', { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file }),
}
