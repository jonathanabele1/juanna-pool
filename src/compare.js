// Your picks next to another player's for the same week: game by game, and how alike the two weeks are.
// Both weeks are merged onto the same sheet, so game i is the same game in each. Their picks on games that haven't
// kicked off come back hidden, so only revealed games are compared.

const pts = g => (g?.pick ? Number(g.points) || 0 : 0)

// how one game compares: same side and points, same side only, opposite sides, one of you has no pick, or still hidden
export function gameMatch(mine, theirs) {
  if (theirs?.hidden) return 'hidden'
  if (!mine?.pick || !theirs?.pick) return mine?.pick || theirs?.pick ? 'one' : 'none'
  if (mine.pick !== theirs.pick) return 'diff'
  return pts(mine) === pts(theirs) ? 'same' : 'pts'
}

// Match: the points you both put on the same side (the smaller of the two on each game), out of the points either of
// you put on the revealed games (the two totals averaged). Two full weeks of 100 make it "points in common, out of 100".
export function compareWeeks(mine, theirs) {
  const rows = theirs.map((t, i) => {
    const m = mine?.[i]
    const same = m && m.fav === t.fav && m.dog === t.dog   // same game; it always is unless the sheet changed
    return { i, mine: same ? m : null, theirs: t, match: gameMatch(same ? m : null, t) }
  })
  const shown = rows.filter(r => r.match !== 'hidden')
  let common = 0, total = 0
  for (const r of shown) {
    const a = pts(r.mine), b = pts(r.theirs)
    total += (a + b) / 2
    if (r.match === 'same' || r.match === 'pts') common += Math.min(a, b)
  }
  const both = shown.filter(r => ['same', 'pts', 'diff'].includes(r.match))
  const differ = shown.filter(r => r.match === 'diff')
  return {
    rows,
    compared: shown.length,
    both: both.length,                                   // games you both picked
    sameSide: both.filter(r => r.match !== 'diff').length,
    exact: both.filter(r => r.match === 'same').length,
    match: total ? common / total : null,                // 0–1, null until there's something to compare
    common, total,
    atStake: differ.reduce((s, r) => s + pts(r.mine) + pts(r.theirs), 0),  // points on games you went opposite ways
  }
}
