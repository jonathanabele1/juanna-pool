// Allowed point values: 2 through 20, or 50 for the Lock of the Year (docs/picks-and-scoring.md).
export const MIN_PTS = 2
export const MAX_PTS = 20
export const LOY_PTS = 50

// typed-in value: snap to the nearest allowed one
export function clampPoints(v) {
  const n = Math.round(Number(v))
  if (n === LOY_PTS) return LOY_PTS
  if (!Number.isFinite(n)) return MIN_PTS
  return Math.min(MAX_PTS, Math.max(MIN_PTS, n))
}

// the − / + buttons: stay inside 2–20; stepping down off the LOY lands on 20
export function stepPoints(cur, d) {
  const n = Number(cur) || 0
  if (n === LOY_PTS) return d < 0 ? MAX_PTS : LOY_PTS
  return clampPoints(n + d)
}
