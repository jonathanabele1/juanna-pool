// Build a week's games from the NFL schedule (ESPN) + DraftKings lines, for weeks with no uploaded sheet yet.
import { sheetName } from './teams.js'

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
        status: 'email',
        pick: 'fav',
        points: 2,
      }
    })
}
