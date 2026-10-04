// Parse OCR text of the weekly "SPREADS, WEEK N" sheet into games.
// Row shape: <fav> <line> <dog> [(H)] <day> [time]

const DAY = /(thurs?|thu|tues?|wed|fri|sat|sun|mon)\.?/i

export function parseWeek(text) {
  const m = text.match(/week\s*(\d+)/i)
  return m ? Number(m[1]) : null
}

export function parseSpreads(text) {
  const games = []
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/[|]/g, ' ').trim()
    // line value: e.g. 2.5, 11.5, 3.0 (OCR sometimes yields "3,5")
    const m = line.match(/^(.+?)\s+(\d{1,2}[.,]\d|\d{2,3})\s+(.+)$/)
    if (!m) continue
    const fav = cleanName(m[1])
    const spread = parseLine(m[2])
    const rest = m[3]
    const dm = rest.match(DAY)
    if (!fav || !dm) continue
    const dogPart = rest.slice(0, dm.index)
    const dogMarkedHome = /\(\s*h\s*\)/i.test(dogPart)
    const dog = cleanName(dogPart.replace(/\(\s*[A-Za-z]\s*\)/g, ''))
    if (!dog) continue
    const time = rest.slice(dm.index + dm[0].length).trim()
    games.push({ fav, dog, spread, day: normDay(dm[1]), time, favHome: favIsHome(fav, dog, m[1], dogMarkedHome) })
  }
  return games
}

function cleanName(s) {
  return s.replace(/[^A-Za-z.\s]/g, '').trim().split(/\s+/)[0] || ''
}

function normDay(d) {
  const k = d.toLowerCase().slice(0, 3)
  return { thu: 'Thurs', tue: 'Tues', wed: 'Wed', fri: 'Fri', sat: 'Sat', sun: 'Sun', mon: 'Mon' }[k]
}

// Lines are always x.0 or x.5; OCR sometimes drops the decimal ("35" -> 3.5).
function parseLine(tok) {
  if (/^\d+$/.test(tok)) return Number(tok.slice(0, -1) + '.' + tok.slice(-1))
  return Number(tok.replace(',', '.'))
}

// Sheet convention: ALL CAPS = home team, lowercase = away; an explicit "(H)" marks home too.
// Returns true/false, or null when the sheet doesn't say.
function favIsHome(fav, dog, favRaw, dogMarkedHome) {
  const upper = s => s === s.toUpperCase()
  if (dogMarkedHome) return false
  if (/\(\s*h\s*\)/i.test(favRaw)) return true
  if (upper(fav) && !upper(dog)) return true
  if (upper(dog) && !upper(fav)) return false
  return null
}
