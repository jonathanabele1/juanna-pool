// Match sheet team names (e.g. "CHIC", "jack", "wash") to ESPN events and compare lines.

const ALIASES = { indy: 'IND', wash: 'WSH', jax: 'JAX', jack: 'JAX', was: 'WSH' }

export function matchTeam(sheetName, team) {
  const s = sheetName.toLowerCase().replace(/[^a-z]/g, '')
  if (!s) return false
  // OCR often reads a lowercase "l" as "I" and a "c" as "e" (e.g. "lv" -> "Iv", "kc" -> "ke")
  const variants = new Set([s, s.replace(/i/g, 'l'), s.replace(/e$/, 'c')])
  return [...variants].some(v => matchExact(v, team))
}

function matchExact(s, team) {
  if (ALIASES[s]) return ALIASES[s] === team.abbr
  if (s === team.abbr.toLowerCase()) return true
  if (s.length < 3) return false
  return [team.location, team.name].some(n => n.toLowerCase().replace(/[^a-z]/g, '').startsWith(s))
}

export function findEvent(g, events) {
  return events.find(e =>
    (matchTeam(g.fav, e.home) && matchTeam(g.dog, e.away)) ||
    (matchTeam(g.fav, e.away) && matchTeam(g.dog, e.home))
  )
}

// Returns { text, changed, delta, flipped, locked } describing the current line from the sheet-favorite's view.
export function currentLine(g, events) {
  const ev = findEvent(g, events)
  if (!ev) return { text: '?', title: 'No matching game found', unknown: true }
  if (!ev.line) return { text: '—', title: ev.state === 'pre' ? 'No line posted' : 'Game started', locked: ev.state !== 'pre' }
  const favTeam = matchTeam(g.fav, ev.home) ? ev.home : ev.away
  const dogTeam = favTeam === ev.home ? ev.away : ev.home
  const { favorite, spread } = ev.line
  const title = `${ev.line.provider || 'Book'} · kickoff ${new Date(ev.kickoff).toLocaleString()}`
  if (favorite && favorite !== favTeam.abbr) {
    return { text: `${dogTeam.abbr} ${spread}`, title: `Favorite flipped! ${title}`, changed: true, flipped: true, delta: null }
  }
  const signed = favorite ? spread : 0 // pick'em -> 0
  const delta = +(signed - g.spread).toFixed(1)
  return { text: String(signed), title, changed: delta !== 0, delta }
}

// Resolve a sheet game to ESPN team objects (for logos/names) plus home/away.
export function resolveGame(g, events) {
  const ev = findEvent(g, events)
  if (!ev) return { event: null, favTeam: null, dogTeam: null, favHome: g.favHome ?? true }
  const favTeam = matchTeam(g.fav, ev.home) ? ev.home : ev.away
  const dogTeam = favTeam === ev.home ? ev.away : ev.home
  const espnFavHome = favTeam === ev.home
  return { event: ev, favTeam, dogTeam, favHome: g.favHome ?? espnFavHome }
}

// A game in progress or finished, from your pick's side: { state, margin, status: 'win'|'loss'|'push' }.
// margin > 0 means your side is covering the sheet spread by that much.
export function coverNow(g, events) {
  const r = resolveGame(g, events)
  const ev = r.event
  if (!ev || !['in', 'post'].includes(ev.state) || ev.scores?.home == null || ev.scores?.away == null) return null
  const favHome = r.favTeam === ev.home
  const fav = favHome ? ev.scores.home : ev.scores.away
  const dog = favHome ? ev.scores.away : ev.scores.home
  const m = fav - dog - (Number(g.spread) || 0)
  const margin = g.pick === 'dog' ? -m : m
  return { state: ev.state, margin, status: margin > 0 ? 'win' : margin < 0 ? 'loss' : 'push' }
}
