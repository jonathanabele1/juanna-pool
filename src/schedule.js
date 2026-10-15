// Build a week's games from the NFL schedule (ESPN) + DraftKings lines, for weeks with no uploaded sheet yet.
import { sheetName } from './teams.js'
import { resolveGame } from './lines.js'

const DAYS = { Mon: 'Mon', Tue: 'Tues', Wed: 'Wed', Thu: 'Thurs', Fri: 'Fri', Sat: 'Sat', Sun: 'Sun' }

function kickoffET(iso) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York', weekday: 'short', hour: 'numeric', minute: '2-digit', hour12: true,
    }).formatToParts(new Date(iso)).map(p => [p.type, p.value]),
  )
  const h = Number(parts.hour) % 12 + (parts.dayPeriod === 'PM' ? 12 : 0)
  const minutes = h * 60 + Number(parts.minute)
  const day = DAYS[parts.weekday]
  // like the sheet: only unusual early Sunday games (e.g. London) get a time
  const time = day === 'Sun' && minutes < 12 * 60 + 30 ? `${parts.hour}:${parts.minute} ${parts.dayPeriod}` : ''
  return { day, time }
}

export function gamesFromEvents(events) {
  return [...events]
    .sort((a, b) => a.kickoff.localeCompare(b.kickoff))
    .map(ev => {
      const favTeam = ev.line?.favorite === ev.away.abbr ? ev.away : ev.home // no line: home team is the placeholder "favorite"
      const dogTeam = favTeam === ev.home ? ev.away : ev.home
      const favHome = favTeam === ev.home
      return {
        fav: sheetName(favTeam.abbr, favHome),
        dog: sheetName(dogTeam.abbr, !favHome),
        spread: ev.line?.spread ?? 0,
        ...kickoffET(ev.kickoff),
        favHome,
        eventId: ev.id,
        favAbbr: favTeam.abbr,
        dogAbbr: dogTeam.abbr,
        hasLine: !!ev.line,
        source: 'schedule',
        pick: null,
        points: 2,
      }
    })
}

// ---- kickoff slots: the games list grouped by when they start (ET), e.g. "Sunday 1:00 PM", "Sunday 4:05 / 4:25 PM" ----
const SHEET_DAYS = { Thurs: 'Thursday', Tues: 'Tuesday', Wed: 'Wednesday', Fri: 'Friday', Sat: 'Saturday', Sun: 'Sunday', Mon: 'Monday' }
const ET = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'long', hour: 'numeric', minute: '2-digit', hourCycle: 'h12' })

function slotOf(g, events) {
  const kickoff = resolveGame(g, events).event?.kickoff
  if (!kickoff) return null
  const p = Object.fromEntries(ET.formatToParts(new Date(kickoff)).map(x => [x.type, x.value]))
  const hour = Number(p.hour) % 12 + (p.dayPeriod === 'PM' ? 12 : 0)
  // one slot per day + hour, so the 4:05 and 4:25 Sunday games land together
  return { key: `${p.weekday}|${hour}`, at: kickoff, day: p.weekday, time: `${p.hour}:${p.minute} ${p.dayPeriod}` }
}

// items: anything with a sheet game at item.g. Returns [{ key, day, when: '4:05 / 4:25 PM', items }] in kickoff
// order. Games we can't match to ESPN fall back to the sheet's day (and time, if it has one), after the rest.
export function groupByKickoff(items, events) {
  const out = new Map()
  for (const x of items) {
    const s = slotOf(x.g, events)
    const key = s ? s.key : `sheet|${x.g.day}|${x.g.time || ''}`
    if (!out.has(key)) out.set(key, { key, day: s ? s.day : SHEET_DAYS[x.g.day] || x.g.day, times: [], first: s?.at || '~', items: [] })
    const grp = out.get(key)
    const time = s ? s.time : x.g.time
    if (time && !grp.times.includes(time)) grp.times.push(time)
    if (s && s.at < grp.first) grp.first = s.at
    grp.items.push({ ...x, at: s?.at || '~' })
  }
  const groups = [...out.values()].sort((a, b) => a.first.localeCompare(b.first))
  for (const grp of groups) {
    grp.items.sort((a, b) => a.at.localeCompare(b.at))  // stable: same kickoff keeps sheet order
    grp.times.sort((a, b) => new Date(`1/1/2000 ${a}`) - new Date(`1/1/2000 ${b}`))
    // "4:05 / 4:25 PM": the AM/PM only once when every time shares it
    const periods = new Set(grp.times.map(t => t.split(' ')[1]))
    grp.when = periods.size === 1 && grp.times.length > 1
      ? `${grp.times.map(t => t.split(' ')[0]).join(' / ')} ${[...periods][0]}`
      : grp.times.join(' / ')
  }
  return groups
}
