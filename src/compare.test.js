import { test } from 'node:test'
import assert from 'node:assert/strict'
import { compareWeeks, gameMatch } from './compare.js'

const g = (pick, points, extra = {}) => ({ fav: 'Bills', dog: 'Jets', pick, points, ...extra })

test('gameMatch sorts each game', () => {
  assert.equal(gameMatch(g('fav', 10), g('fav', 10)), 'same')
  assert.equal(gameMatch(g('fav', 10), g('fav', 4)), 'pts')
  assert.equal(gameMatch(g('fav', 10), g('dog', 10)), 'diff')
  assert.equal(gameMatch(g(null, null), g('dog', 10)), 'one')
  assert.equal(gameMatch(g(null, null), g(null, null)), 'none')
  assert.equal(gameMatch(g('fav', 10), g(null, null, { hidden: true })), 'hidden')
})

test('identical weeks match 100%, opposite weeks 0%', () => {
  const week = [g('fav', 60), g('dog', 40)]
  assert.equal(compareWeeks(week, week).match, 1)
  assert.equal(compareWeeks(week, [g('dog', 60), g('fav', 40)]).match, 0)
})

test('match is the points in common out of 100', () => {
  const mine = [g('fav', 50), g('dog', 30), g('fav', 20)]
  const theirs = [g('fav', 20), g('dog', 30), g('dog', 50)]
  const c = compareWeeks(mine, theirs)
  assert.equal(c.common, 50)    // 20 + 30
  assert.equal(c.total, 100)
  assert.equal(c.match, 0.5)
  assert.equal(c.sameSide, 2)
  assert.equal(c.exact, 1)
  assert.equal(c.atStake, 70)
})

test('hidden games are left out', () => {
  const mine = [g('fav', 50), g('dog', 50)]
  const theirs = [g('fav', 50), g(null, null, { hidden: true })]
  const c = compareWeeks(mine, theirs)
  assert.equal(c.compared, 1)
  assert.equal(c.match, 1)
})

test('no picks of your own: nothing in common', () => {
  const c = compareWeeks(null, [g('fav', 50)])
  assert.equal(c.match, 0)
  assert.equal(c.both, 0)
})
