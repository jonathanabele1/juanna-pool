// What the week card's pill popover says about one game: both teams (away first) with the score, the game's status,
// the pick and, while it can still change, the chance it covers. Your own week card and another player's both use it.
import { resolveGame } from './lines.js'
import { sideOdds, pctText, pushText } from './odds.js'

// g: the sheet game with the pick; res: the server's result for it; odds: the game's cover odds;
// lineMoved: the line is off the sheet's (a not-started game's cover odds are only worth showing then)
export function gamePop(g, res, events, { odds = null, lineMoved = false } = {}) {
  const r = resolveGame(g, events), ev = r.event
  const scoreOf = key => {
    if (!ev || ev.state === 'pre') return null
    const team = key === 'fav' ? r.favTeam : r.dogTeam
    return ev.scores?.[team === ev.home ? 'home' : 'away'] ?? res?.[`${key}Score`] ?? null
  }
  const side = key => {
    const t = key === 'fav' ? r.favTeam : r.dogTeam
    return { abbr: t?.abbr || (g[key] || '').toUpperCase(), logo: t?.logo, score: scoreOf(key), mine: g.pick === key }
  }
  const teams = r.favHome ? [side('dog'), side('fav')] : [side('fav'), side('dog')]   // away first
  const l = ev?.live
  const when = !ev ? `${g.day || ''} ${g.time || ''}`.trim()
    : ev.state === 'post' ? (/OT/.test(ev.detail || '') ? 'Final · OT' : 'Final')
    : ev.state === 'in' ? (l?.halftime ? 'Halftime' : [l?.quarter, l?.clock].filter(Boolean).join(' · ') || 'Live')
    : new Date(ev.kickoff).toLocaleString([], { weekday: 'short', hour: 'numeric', minute: '2-digit' })
  const pick = pickLabel(g, events)
  const pending = (res?.outcome || 'pending') === 'pending'
  const o = g.pick && pending && (ev?.state === 'in' || lineMoved) ? sideOdds(odds, g.pick) : null
  const chance = o && [`${pctText(o.cover)} to cover`, pushText(o)].filter(Boolean).join(' · ')
  return { teams, when, pick, chance }
}

// "BUF −3 · 10 pts", "No pick", or "Pick hidden" (another player's, before kickoff)
export function pickLabel(g, events) {
  if (g?.hidden) return 'Pick hidden'
  if (!g?.pick) return 'No pick'
  const r = resolveGame(g, events), t = g.pick === 'fav' ? r.favTeam : r.dogTeam
  const line = g.hasLine === false ? '' : !g.spread ? ' PK' : g.pick === 'fav' ? ` −${g.spread}` : ` +${g.spread}`
  return `${t?.abbr || (g[g.pick] || '').toUpperCase()}${line} · ${Number(g.points) || 0} pts`
}
