const JSON_HEADERS = { 'Content-Type': 'application/json' }

async function call(url, opts) {
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
export const getTeamCovers = beforeWeek => call(`/api/teams?before_week=${beforeWeek}`)

export const admin = {
  users: () => call('/api/admin/users'),
  createUser: body => send('POST', '/api/admin/users', body),
  updateUser: (id, body) => send('PATCH', `/api/admin/users/${id}`, body),
  week: n => call(`/api/admin/weeks/${n}`),
  setDeadlines: (n, overrides) => send('PUT', `/api/admin/weeks/${n}/deadlines`, { overrides }),
  setPick: (userId, n, body) => send('PATCH', `/api/admin/picks/${userId}/${n}`, body),
  deleteLines: n => call(`/api/admin/weeks/${n}/lines`, { method: 'DELETE' }),
  setAnnouncement: text => send('PUT', '/api/admin/announcement', { text }),
  restore: file => call('/api/admin/restore', { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file }),
}
