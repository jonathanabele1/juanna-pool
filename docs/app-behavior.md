# App Behavior

## Weeks and persistence
- Everything is stored in one SQLite file, **`backend/data/pool.db`** (`/data/pool.db` on Railway): accounts, each
  week's lines and sheet image, and every player's picks. See [deploy.md](deploy.md) for accounts and backups.
- The week bar (1–18) switches weeks. Saved weeks show their score; the current NFL week is marked "now".
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
- The first tap asks how to send: Gmail, Outlook or Mail app, plus your team name. It's saved on the account, and
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

## Season stats
Total, weekly average, record vs spread, best/worst week, points earned vs wagered, cover rate by confidence tier,
favorite/underdog and home/away tendencies, Lock of the Year result, biggest hit/miss, running total.

## The rest of the pool
- **League** tab (third, after Season stats). One page: the week on top (‹ › to change weeks), the season below.
  Each section opens with three highlights: week leader/winner, your place, pool average; season leader (and lead),
  your place (and points back), best single week. *Week*: every player's score for the week, with a column each for Score, Live
  (if every game on now ended as it stands), Max and Live max (columns show only when they apply). Tap a header to sort
  by it, tap again to flip. While games are live it sorts by Live by default (with ▲/▼ for places gained or lost vs.
  the final games only) and refreshes every 30s.
  *Season*: total (with points behind the leader), average, record, weeks won (finished weeks only), and ▲/▼ for
  places moved since the week before the latest one with results. Tap a player to open their page.
- A player's page shows their picks week by week (read-only) and their season stats. **Another player's pick on a
  game stays hidden until that game kicks off**: the server never sends it, admins included.
- Season stats has a "Viewing" picker to look at anyone's season.
- Once a game kicks off, its card shows the pool's split (% and count per side, and whether you're with the
  pool). **Details** lists every player's pick, points and result for that game.
- **Public betting**: DraftKings' published betting splits (% of bets and % of money on each side of the spread),
  scraped from DK Network every 10 minutes before kickoff. The last split seen before kickoff is kept in the
  `splits` table, so it still shows afterward. If DraftKings can't be reached, the row just doesn't show.

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
