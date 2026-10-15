// The pool's picks on each game (revealed at kickoff) and DraftKings' public betting, keyed to sheet games.

const norm = s => (s || '').toLowerCase().replace(/[^a-z]/g, '')

// same key the server stores picks under (backend/db.py game_key)
export const gameKey = g => (g.eventId ? `ev:${g.eventId}` : `nm:${norm(g.fav)}|${norm(g.dog)}`)

export const poolByKey = pool => Object.fromEntries((pool?.games || []).map(p => [p.key, p]))

// Team colors for a two-sided bar: each team's main color, unless they're too alike (or too pale to see on
// white), in which case the second team tries its alternate color, then a neutral gray.
const rgb = h => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255] }
const hex = c => (c && /^#?[0-9a-f]{6}$/i.test(c) ? `#${c.replace('#', '')}` : null)
const light = h => { const [r, g, b] = rgb(h); return (0.299 * r + 0.587 * g + 0.114 * b) / 255 }
const far = (a, b) => Math.hypot(...rgb(a).map((v, i) => v - rgb(b)[i])) > 110
const usable = h => h && light(h) < 0.82
export function teamColors(a, b) {
  const first = [hex(a?.color), hex(a?.alternateColor)].find(usable) || '#475569'
  const second = [hex(b?.color), hex(b?.alternateColor)].find(h => usable(h) && far(h, first)) || '#94a3b8'
  return [first, second]
}
// readable text in a team color (very light colors fall back to slate)
export const textColor = h => (light(h) > 0.62 ? '#334155' : h)

export const pct = (n, total) => (total ? Math.round((100 * n) / total) : 0)
