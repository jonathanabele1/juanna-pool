// Cover odds from the server (backend/cover.py). Each game's are the favorite's ({ fav, push }), so they follow
// whichever side you pick, even before you save.

// your side's chance to cover and to push
export function sideOdds(odds, pick) {
  if (!odds || !pick) return null
  return { cover: pick === 'fav' ? odds.fav : Math.max(0, 1 - odds.fav - odds.push), push: odds.push }
}

// never "0%" or "100%" while the game can still change
export const pctText = p => (p < 0.005 ? '<1%' : p > 0.995 ? '>99%' : `${Math.round(p * 100)}%`)

// a push is only worth mentioning when it's a real chance (whole-number spreads, late, on the number)
export const pushText = o => (o?.push >= 0.05 ? `${pctText(o.push)} push` : '')

export const tone = p => (p >= 0.7 ? 'good' : p <= 0.3 ? 'bad' : 'even')
