// The pool's picks on each game (revealed at kickoff) and DraftKings' public betting, keyed to sheet games.

const norm = s => (s || '').toLowerCase().replace(/[^a-z]/g, '')

// same key the server stores picks under (backend/db.py game_key)
export const gameKey = g => (g.eventId ? `ev:${g.eventId}` : `nm:${norm(g.fav)}|${norm(g.dog)}`)

export const poolByKey = pool => Object.fromEntries((pool?.games || []).map(p => [p.key, p]))

// Team colors for a two-sided bar: each team's main color, unless it's too alike the other team's or too hard
// to see on the card (pale on the light theme, dark on the dark theme), in which case it tries the alternate color,
// then its own color lifted until it shows, then a neutral gray.
const rgb = h => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255] }
const hex = c => (c && /^#?[0-9a-f]{6}$/i.test(c) ? `#${c.replace('#', '')}` : null)
const far = (a, b) => Math.hypot(...rgb(a).map((v, i) => v - rgb(b)[i])) > 110
// WCAG contrast between two colors
const lum = h => rgb(h).map(v => v / 255).map(v => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
  .reduce((t, v, i) => t + v * [0.2126, 0.7152, 0.0722][i], 0)
export const contrast = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05) }
const mix = (a, b, t) => `#${rgb(a).map((v, i) => Math.round(v + (rgb(b)[i] - v) * t).toString(16).padStart(2, '0')).join('')}`
// the card the colors sit on, per theme (--card in style.css)
const CARD = { light: '#ffffff', dark: '#141c2b' }
// h, moved toward white (dark theme) or black (light theme) just far enough to reach `min` contrast with the card
export function readable(h, dark, min) {
  const bg = dark ? CARD.dark : CARD.light, to = dark ? '#ffffff' : '#000000'
  for (let t = 0; t <= 1; t += 0.05) { const c = mix(h, to, t); if (contrast(c, bg) >= min) return c }
  return to
}
const BAR_MIN = 1.6   // a bar segment has to stand out from the card
export function teamColors(a, b, dark = false) {
  const bg = dark ? CARD.dark : CARD.light
  const usable = h => h && contrast(h, bg) >= BAR_MIN
  const own = t => hex(t?.color) && readable(hex(t.color), dark, BAR_MIN)
  const first = [hex(a?.color), hex(a?.alternateColor)].find(usable) || own(a) || (dark ? '#64748b' : '#475569')
  const second = [hex(b?.color), hex(b?.alternateColor), own(b)].find(h => usable(h) && far(h, first)) || (dark ? '#cbd5e1' : '#94a3b8')
  return [first, second]
}
// readable text in a team color: the same hue, lightened (dark theme) or darkened (light theme) until it reads
export const textColor = (h, dark = false) => readable(h, dark, 4.5)

export const pct = (n, total) => (total ? Math.round((100 * n) / total) : 0)
