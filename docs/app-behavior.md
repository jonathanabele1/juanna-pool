# App Behavior

## Weeks and persistence
- Everything is stored in one SQLite file, **`backend/data/pool.db`** (`/data/pool.db` on Railway): accounts, each
  week's lines and sheet image, and every player's picks. See [deploy.md](deploy.md) for accounts and backups.
- The week bar (1–18) switches weeks. Saved weeks show their score; the current NFL week is marked "now". The
  selected week always sits in the middle of the strip (weeks 1 and 18 too); ← / → step through weeks when it has focus.
- **Save** stores your picks for the week. Only games with a team picked are saved.
- Re-uploading an image replaces the matchups but keeps your pick/points for any matchup that still exists.
- "Clear my picks" removes your saved picks for that week (not allowed once any of its deadlines have passed).
- A week with saved picks opens read-only (with an "Edit picks" button); Cancel discards changes and goes back to that view.
- The week card shows score, record and max first, then a strip with one pill per game (colored by result). Tap a pill
  for a small popover with that game's score and status; tap the popover to jump to the game. Send picks and Edit picks
  sit under the results.

## Picking
- Every game starts with no pick. Tap a team to pick it; tap it again to clear the pick. Points can only be
  set on a picked game.
- A row of pills above the games picks what to show: **All** (kickoff order, the default), **Live** (with a count),
  **Pending** (not kicked off), **Final**, **Top points** (every game, your biggest picks first), and while editing
  **No pick** (open games still to pick). A pill only shows while it has games; tap the active pill again for All.
- While editing, each card has quick presets (10, 20, ★ LOY) next to the − / + stepper. Tapping a preset again
  goes back to 2.
- **Press and hold (or double-click) a team** for a small card with its season so far, from the weeks before this
  one on your saved sheets: overall record, ATS, ATS as favorite/underdog (whichever it is in this game), your record
  and net points picking them and fading them, and its last 5 ATS results. Holding doesn't change the pick. The next
  tap anywhere closes it, and that tap doesn't press anything else.
- A game with no pick is a skip (−20) only once it kicks off. Before that it's just open.

## Sending picks
- Once a week has saved picks, its card shows **✉ Send picks**. It opens a new email from the player's own
  account, addressed to that week's league address (set in Admin → League email addresses), with the subject and
  picks filled in. They check it and send it themselves. It has to come from their own mailbox: the league goes by
  when it was sent, and a disputed pick is settled by forwarding the original from Sent.
- The email has your **saved** picks only, in sheet order with the sheet's team names, under "Week N." and your
  team name. Picks on games that already kicked off are left out (they went in an earlier email, e.g. Thursday's)
  and the header becomes "Rest of week N.", unless every pick has kicked off.
- Send picks first shows a confirmation: picks made (e.g. 14/14), points used (e.g. 100/100), the league address, the
  email app and a preview of the email, with a note for anything off (games without a pick, points left or over, 4
  double-digit picks, no league address). Its button opens the email.
- The first send asks how to send: Gmail, Outlook or Mail app, plus your team name. It's saved on the account, and
  **account menu → Email settings** changes it later.
  - Phones: the Gmail or Outlook app opens. If it isn't installed, the website opens instead.
  - Desktop: Gmail or outlook.com opens in a new tab. An optional Gmail address picks the right account when
    someone is signed into several. Mail app means a plain `mailto:` link.
- Thursday flow: pick the Thursday game, Save, Send picks. Sunday: Edit picks, pick the rest, Save, Send picks.
- Older saves that used Email/Sent/Skip still load: Email and Sent picks keep their team, Skip becomes no pick.

## Scoring (computed by the backend from ESPN final scores)
- A pick wins if that side covers the **sheet** spread (not the live line). A push earns half the points (2½ for a 5).
- Weekly score = points on covered picks + half points on pushes + manual adjustment.
- No penalties are applied automatically. Any penalty (over 100, four double-digits, skipped games, late picks, out-of-order, etc.) is entered by hand in the week's **Adjustment** field on the Admin page.
- Final results are cached in the database, so past weeks still score if ESPN is unreachable.

## Cover odds and Win %
How both are worked out, how well they hold up, and how to rebuild the data: [odds.md](odds.md).
- **Cover odds**: the chance a pick covers the sheet spread. Shown on a live game card ("41% to cover"), on the
  DraftKings pill before kickoff when the line has moved ("KC 46%"), in the week card's pill popover and on grid
  tiles. Nothing shows when it's a coin flip.
- **Win %**: League → Week, each player's chance to finish first this week among the players here. Picks on games
  that haven't kicked off stay hidden and aren't used.

## Accuracy
An app stat, not a league rule: how close each player's final picks came, so a near miss counts for more than a
blowout. `backend/scoring.py` (`pick_accuracy`, `accuracy`).
- Each decided pick: a cover or push is **100%**, a miss loses 100/14 (~7%) per point it missed by, down to
  **0%** at 14 or more (missed by 1: 93%, by 7: 50%).
- Week and season accuracy are the average over decided picks, **weighted by points** (a 20 counts ten times a 2).
  The LOY's 50 counts as 20. Season accuracy runs over every pick of the season, not an average of the weeks.
- Shown in League → Week (*Acc* column, sortable, phones included), the Season table, and a tile on
  Season stats.
- Picks → week card (yours or another player's): an **Accuracy** tile beside Score, Record and Max once a game is
  final or on (a › in its label corner says it opens). While games are on, a red second number is the **live
  accuracy**: the picks on now rated as they stand, with the final ones (`liveAccuracy` in the week score). Tapping it
  opens each rated pick's result and accuracy, biggest points first, live picks in red ("Covering by 3", "Down 2½")
  (`src/components/AccuracyDialog.vue`). Its header (week, %, live %, close) stays pinned while the picks scroll; the
  book button shows how it's scored; a tap outside closes it. With four tiles, phones show them 2×2.
- Live numbers on the week card (score, record, max, accuracy) are the red second number in each tile. A single
  "● Live" badge next to the week title stands for all of them.

## Season stats
Total, weekly average, accuracy, record vs spread, best/worst week, points earned vs wagered, cover rate by confidence tier,
favorite/underdog and home/away tendencies, Lock of the Year result, biggest hit/miss, running total.

## The rest of the pool
- **League** tab (third, after Season stats). One page: the week strip on top (the same as the Picks tab: tap a
  week or swipe along it, your score under each), the week, then the season through that week (an earlier week shows
  the season table as it stood then, ▲/▼ included; `GET /api/standings/season?through=N`).
  Each section opens with three highlights: week leader/winner, your place, pool average; season leader (and lead),
  your place (and points back), best single week. *Week*: every player's score for the week, with a column each for Score, Live
  (if every game on now ended as it stands), Win % (chance to win the week, see [odds.md](odds.md)), Max and Live max
  (columns show only when they apply; on phones Win % takes Live max's place). Tap a header to sort
  by it, tap again to flip. While games are live it sorts by Live by default (with ▲/▼ for places gained or lost vs.
  the final games only) and refreshes every 30s.
  *Season*: total (with points behind the leader), average, record, weeks won (finished weeks only), and ▲/▼ for
  places moved since the week before the latest one with results. Tap a player to view them: it switches to them and
  opens Picks (on that week, from the week table).
- **Viewing switcher** (the pill next to the account icon, "You ▾"): picks whose Picks and Season stats tabs you see.
  The menu lists you first, then everyone else with their team name. While viewing someone else the pill turns blue,
  Picks shows their week read-only (with their own week bar scores) and Season stats shows their season. "My picks"
  / "My stats" (or picking yourself in the menu) goes back. Your own picks stay loaded underneath, so unsaved edits
  survive a look at someone else. **Another player's pick on a game stays hidden until that game kicks off, or
  Sunday 1:00 PM ET** (when every pick is in, per the league), whichever comes first: from then on every pick of the
  week shows (`deadlines.reveal_at`). Until then the server never sends it, admins included.
- **Their pill strip** sits on their week card like yours does on the Picks tab (one pill per game with its points,
  in sheet order; a lock while a pick is hidden; tap one to jump to the game). **Compare with my picks** (a dropdown
  under it, closed by default, `src/compare.js`) adds a row of your saved picks under theirs. While it's open, each
  game card also says "You: NYJ 12" (or "same pick"). Tiles: **Match**, the points you both put on the same side
  (the smaller of the two on each game) out of the points on the games you can compare (the two totals averaged,
  so two full weeks are "out of 100"); **Same side** (games you both picked, how many exactly, and the points on
  games you split); **Head to head** (your score vs theirs, live while games are on). Only games whose
  picks are revealed count, so nothing hidden leaks.
- **Team names** (set in Email settings) show above the week card's title and under the name on Season stats.
- Once a game kicks off (or from Sunday 1:00 PM ET), its card shows the pool's split (% and count per side, and whether you're with the
  pool). **Details** lists every player's pick, points and result for that game.
- **Public betting**: DraftKings' published betting splits (% of bets and % of money on each side of the spread),
  scraped from DK Network every 10 minutes before kickoff. The last split seen before kickoff is kept in the
  `splits` table, so it still shows afterward. If DraftKings can't be reached, the row just doesn't show.

## Appearance
- Account menu → **Theme**: Light, Dark or Auto (follows the device; the default). Kept per browser.

## Test live mode (admins)
- Account menu → **🧪 Test live mode** (shown in admin mode). A purple banner shows while it's on; "Turn off" ends it.
- The current week (and later ones) pretend to be mid-game: ~40% of games final, ~30% live, the rest not started.
  Live games move along every 30s (a game runs Q1 to the 4th quarter in 30 minutes, then starts over). Finished
  weeks stay real.
- Only the admin who turned it on sees it, and nothing fake is saved. Other players' picks on games that haven't
  *really* kicked off are replaced with made-up picks, so it can't reveal hidden picks. The Admin tab always shows
  real data. Turning admin mode off also turns test mode off.

## Accounts (Admin tab)
- **Hide from league** leaves an account (e.g. a test account) out of everything other players see: the League
  tab, the pool split on each game, the player list and player pages. The hidden account still sees itself.
  **Show in league** puts it back. Nothing is deleted.
- **Delete…** removes the account and all of its picks for good (after an on-page confirm). You can't delete
  yourself.
