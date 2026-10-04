import test from 'node:test'
import assert from 'node:assert/strict'
import { parseSpreads, parseWeek } from './parse.js'

const sample = `SPREADS, WEEK 4
Fav Line Dog
pitt 2.5 CLEVE Thurs.
indy 3.5 wash (H) Sun. 9:30 AM
BALT 11.5 tenn Sun.
NO 2.5 atl Mon.`

test('week number', () => assert.equal(parseWeek(sample), 4))

test('games', () => {
  const g = parseSpreads(sample)
  assert.equal(g.length, 4)
  assert.deepEqual(g[1], { fav: 'indy', dog: 'wash', spread: 3.5, day: 'Sun', time: '9:30 AM', favHome: false })
  assert.equal(g[2].spread, 11.5)
  assert.equal(g[3].day, 'Mon')
})

test('OCR dropped decimal', () => {
  const g = parseSpreads('gb 35 TB Sun.\nke 45 LV Sun.\nBALT 115 tenn Sun.')
  assert.deepEqual(g.map(x => x.spread), [3.5, 4.5, 11.5])
})

import { currentLine, matchTeam } from './lines.js'

const T = (abbr, location, name) => ({ abbr, location, name })
const ev = (home, away, line, state = 'pre') => ({ home, away, line, state, kickoff: '2026-10-04T17:00Z' })

test('team matching', () => {
  assert.ok(matchTeam('wash', T('WSH', 'Washington', 'Commanders')))
  assert.ok(matchTeam('indy', T('IND', 'Indianapolis', 'Colts')))
  assert.ok(matchTeam('CINCI', T('CIN', 'Cincinnati', 'Bengals')))
  assert.ok(matchTeam('gb', T('GB', 'Green Bay', 'Packers')))
  assert.ok(!matchTeam('ne', T('NYJ', 'New York', 'Jets')))
})

test('line change detection', () => {
  const BUF = T('BUF', 'Buffalo', 'Bills'), NE = T('NE', 'New England', 'Patriots')
  const g = { fav: 'BUFF', dog: 'ne', spread: 6.5 }
  assert.equal(currentLine(g, [ev(BUF, NE, { favorite: 'BUF', spread: 7 })]).delta, 0.5)
  assert.equal(currentLine(g, [ev(BUF, NE, { favorite: 'BUF', spread: 6.5 })]).changed, false)
  assert.equal(currentLine(g, [ev(BUF, NE, { favorite: 'NE', spread: 1 })]).flipped, true)
  assert.equal(currentLine(g, [ev(BUF, NE, null, 'in')]).locked, true)
})

test('home/away from case and (H)', () => {
  const g = parseSpreads('pitt 2.5 CLEVE Thurs.\nBALT 11.5 tenn Sun.\nindy 3.5 wash (H) Sun.')
  assert.deepEqual(g.map(x => x.favHome), [false, true, false])
})

test('OCR confusions still match', () => {
  assert.ok(matchTeam('Iv', T('LV', 'Las Vegas', 'Raiders')))
  assert.ok(matchTeam('ke', T('KC', 'Kansas City', 'Chiefs')))
  assert.ok(!matchTeam('ne', T('NYJ', 'New York', 'Jets')))
})
