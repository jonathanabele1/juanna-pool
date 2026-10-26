# Cover Odds and Win %

Two estimates the app shows on game day, and how they're worked out:

1. **Cover odds**: the chance a pick covers the **sheet** spread, from the score, the clock, who has the ball and
   where. Live and before kickoff.
2. **Win %**: each player's chance to finish first this week, built on the cover odds.

Both are estimates, not league results. Scoring (`backend/scoring.py`) never uses them.

| Piece | Where |
|---|---|
| Cover odds model | `backend/cover.py` |
| The table it reads | `backend/cover_table.json` (≈740 KB) |
| Builds and checks the table | `scripts/build_cover_table.py` |
| Live clock, field position, saved line → odds per pick and per game | `backend/scoring.py` (`pick_odds`, `game_odds`) |
| Win % | `backend/winchance.py` |
| Shown in | `src/components/GameRow.vue`, `GameTile.vue`, `src/PicksView.vue`, `src/StandingsView.vue`, helpers in `src/odds.js` |
| Tests | `backend/test_cover.py`, `backend/test_winchance.py`, `backend/test_league.py` |

---

## 1. Cover odds

### The idea

Take every NFL play from 2012–2025. For each one, note the situation (time left, margin, who has the ball and where)
and how the margin *actually* changed between then and the final whistle. To price a live game, look up games that
were in the same spot and ask how often the margin moved enough to cover.

Real scores keep the things a smooth formula gets wrong: margins pile up on 3 and 7, a team up 4 with the ball and 6
seconds left just kneels, and a team up 3 laying 3 with two minutes left often ends right on the number.

### The table (`cover_table.json`)

Built from [nflverse play-by-play](https://github.com/nflverse/nflverse-data/releases/tag/pbp), regular season and
playoffs. Each row is the state *before* a play, from the point of view of the team with the ball. Plays with no
team in possession (timeouts, ends of quarters) are skipped.

A **cell** is a spot in the game, and holds the spread of "how the margin changed by the end" for that spot:

| Dimension | Bins |
|---|---|
| Time left (regulation) | 0–15s, 15–30s, 30–60s, 1:00–1:30, 1:30–2:00, 2–3, 3–4, 4–5, 5–7, 7–10, 10–15 min, then every 5 min to 60:00 |
| Time left (overtime) | 0–2, 2–5, 5–10 min on the OT clock |
| Margin, team with the ball | ≤−17, −16..−9, −8..−4, −3..−1, 0, 1..3, 4..8, 9..16, ≥17 |
| Field position (yards to go) | 1–10, 11–20, 21–40, 41–60, 61–80, 81–99 |

- **Every game counts once per cell**, however many plays it ran from that spot (a penalty and a replayed down are
  one sample, not two).
- **A cell needs 80 games** to be used. Thinner spots fall back, in order: the same time and margin with a coarser
  field zone (red zone / 21–60 / own side), then any field position, then any margin. The last few seconds of a
  game are thin, so the fallback matters most there.
- Each cell also stores its average margin change and the average market line of the teams in it (used below).

### Pricing a pick (`cover.odds`)

Inputs: the pick's current margin, the number it needs to beat (3.5 for a favorite laying 3.5, −3.5 for the dog
getting 3.5), seconds left, overtime or not, whether its team has the ball, field position, and the market line.

1. **Find the cell** for the team with the ball (its margin, time left, yards to go).
2. **Lean toward the better team.** A 7-point favorite gains more over the rest of a game than a pick'em team does.
   The cell's outcomes are reweighted (exponential tilting) so the average change matches this game's market line,
   scaled by the time left. Reweighting keeps the mass where it is, so 3s and 7s stay 3s and 7s.
3. **Add up** the outcomes that beat the number (cover), land on it (push), or fall short (miss).

When nobody has the ball (halftime, between scores) it averages the two cases, each team getting it at its own 25.

### The market line is an even bet

The app saves each game's DraftKings line from ESPN **before kickoff** (ESPN drops it once a game starts; it's the
`results.line` column). That line is treated as the margin each side is equally likely to beat (the median), not
the average margin. With real scores the two differ a little, and treating it as the average made every favorite
about 53% to cover its own line. So:

- Before kickoff, a sheet line that matches the market is **exactly 50%**.
- The odds move off 50% only when the line has moved since the sheet. Through a key number it's worth more:

| Sheet | Market | Chance on the sheet line |
|---|---|---|
| −2.5 | −2.5 | 50% |
| −2.5 | −3 | 54% (games lined at 3 land on exactly 3 about 7–9% of the time) |
| −2.5 | −3.5 | 57% |
| −6.5 | −7 | 52% |
| −3 | −3 | 46% cover, 7% push, 46% miss |

With no saved line (e.g. a game that had already started when the app first saw it), the sheet line stands in.

### How well it works

Built on 2012–2023, then scored on 30,000 plays from 2024–25 it hadn't seen. It was compared with two simpler
approaches: a normal curve (final margin ~ Normal(margin + line × time left, 13.5 × √time left)) and backing a margin
out of a win probability. Log loss, lower is better:

| Part of the game | Table | Normal curve | From win probability |
|---|---|---|---|
| Whole game | **0.527** | 0.559 | 0.583 |
| Q1–Q3 | **0.602** | 0.613 | 0.602 |
| Q4, 15:00–5:00 | **0.372** | 0.412 | 0.403 |
| Last 5:00 | **0.267** | 0.390 | 0.509 |
| Last 1:00 | **0.193** | 0.464 | 1.432 |

Calibration: when it said 10–20%, 20–30%, … 90–100%, the actual cover rate was within about 2 points every time.
The gain is biggest late in games, which is when people check their phones most.

Tried and dropped:
- **ESPN's win probability** (`situation.lastPlay.probability`). Worst of the three late in games, so nothing uses it.
- **The line as an extra table dimension**, so each cell's shape came from similarly lined games. Thinner cells made
  live odds slightly worse (0.534), and the key-number effect it was after is within the noise of the data.

### Limits

- Ties at the end of regulation and overtime are handled by the data, but overtime cells are thin (few OT games), and
  the 2025 regular-season OT rule change is only one season of it.
- Timeouts and down & distance aren't used. Field position and possession carry most of that.
- The table describes the average NFL game. It knows nothing about injuries, weather or a backup quarterback
  beyond what the market line already says.

---

## 2. Where cover odds show up

The rule: show the number only where it says something. A coin flip shows nothing.

- **Live game card**: on the right of the down-and-distance box, "41% to cover". Green at 70% or more, red at 30% or
  less. A second line gives the push chance when it's 5% or more.
- **Before kickoff**: only when DraftKings' line has moved off the sheet's. The DraftKings pill adds your side's
  chance, or the side the move helps if you haven't picked: "DraftKings 3 ▲ +0.5 | KC 46%" means you took KC +2.5
  and the move went against you.
- **Week card popover** (tap a pill): one line, "53% to cover", for a live game or a moved line.
- **Desktop grid tiles**: after the live status, "Short by ½ · 53%".
- Never "0%" or "100%" while a game can still change: "<1%" and ">99%" instead.

**API.** `GET /api/weeks/{n}` (and a player's week) carries `odds: {eventId: {fav, push}}`, the **favorite's** chance
per game, for games on now or not started. Because it's per game, the number follows whichever side is picked, even
before saving. Each scored pick also gets `odds: {cover, push}` from its own side. A game marked live with no saved
clock gets no odds (rather than wrong ones).

---

## 3. Win % (League → Week)

Each player's chance to finish **first this week among the players in the app**. It's not the whole Juanna pool,
whose picks the app doesn't have. A tie is broken by record (the league's weekly tiebreaker), then split.

### How it's worked out

`backend/winchance.py` plays the rest of the week out 3,000 times:

- **Games on now** end by their cover odds: favorite covers, push, or underdog covers. Every player's pick on that
  game pays off from the **same** result, so players on the same side rise and fall together, and players on
  opposite sides swing apart.
- **Games that haven't kicked off** don't use anyone's actual picks (see below). Each player's points on those games
  are spread evenly over them, and each one is a coin flip.
- Finished games are already in everyone's score.

In each run, the top score (then record) wins, and tied players split it. A player's Win % is the share of runs they
win.

### Hidden picks stay hidden

Another player's pick is hidden until its game kicks off (or Sunday 1 PM ET). If Win % used those picks, you could save different picks
of your own and watch your Win % move to work out a friend's side. So for games that haven't started, the only
thing used is each player's **total** points on them, which the Max column already reveals. A test checks that
flipping a hidden pick's side changes nobody's Win %.

The cost: before those games start, two friends with identical picks look a little less tied than they really are,
since their coin flips are separate. Once a game kicks off, every pick on it is used exactly.

### When it says 0% or 100%

A simulation can miss a long shot, so it only says 0% or 100% when it's settled:

- **0%**: your Max can't reach the leader's current score.
- **100%**: nobody else's Max can reach your current score (or you're the only player).
- Anything else is kept between "<1%" and ">99%".

### Details

- Same game state, same answer: each run is seeded from the state, so the number doesn't flicker between
  30-second refreshes. Every viewer polling the same state shares one cached result.
- It takes about 0.08s with 30 players and 13 live games.
- The column shows while the week is still being decided. On phones it takes Live max's place, since five number
  columns don't fit beside the names. Desktop shows both. Tap the header to sort by it.

---

## Rebuilding the table

Once a season (or to change the bins):

```sh
# download play_by_play_<year>.parquet files from the nflverse pbp release into a folder
pip install pandas pyarrow            # only the build needs these; the app doesn't
python scripts/build_cover_table.py PATH_TO_PARQUET_FOLDER
python -m unittest backend.test_cover backend.test_winchance
```

The script builds on every season but the last two, prints the held-out scores and calibration above, then
rebuilds on all seasons and writes `backend/cover_table.json`. Change `TEST` in the script when a new season is
added. If the held-out log loss gets worse than the normal curve's anywhere, look before shipping.
