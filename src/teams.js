// How the weekly sheet abbreviates each team (ESPN abbreviation -> sheet name).
// On the sheet ALL CAPS = home team, lowercase = away team.
export const SHEET_NAMES = {
  ARI: 'ariz', ATL: 'atl', BAL: 'balt', BUF: 'buff', CAR: 'car', CHI: 'chic', CIN: 'cinci', CLE: 'cleve',
  DAL: 'dal', DEN: 'denv', DET: 'det', GB: 'gb', HOU: 'hous', IND: 'indy', JAX: 'jack', KC: 'kc',
  LV: 'lv', LAC: 'lac', LAR: 'lar', MIA: 'miami', MIN: 'minn', NE: 'ne', NO: 'no', NYG: 'nyg',
  NYJ: 'nyj', PHI: 'phil', PIT: 'pitt', SF: 'sf', SEA: 'seat', TB: 'tb', TEN: 'tenn', WSH: 'wash',
}

export const sheetName = (abbr, isHome) => {
  const base = SHEET_NAMES[abbr] || abbr.toLowerCase()
  return isHome ? base.toUpperCase() : base
}
