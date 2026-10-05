# App Behavior

## Weeks and persistence
- Everything is stored in one SQLite file, **`backend/data/pool.db`** (`/data/pool.db` on Railway): accounts, each
  week's lines and sheet image, and every player's picks. See [deploy.md](deploy.md) for accounts and backups.
- The week bar (1–18) switches weeks. Saved weeks show their score; the current NFL week is marked "now".
- **Save** stores your picks for the week. Only games with a team picked are saved.
- Re-uploading an image replaces the matchups but keeps your pick/points for any matchup that still exists.
- "Clear my picks" removes your saved picks for that week (not allowed once any of its deadlines have passed).
- A week with saved picks opens read-only (with an "Edit picks" button); Cancel discards changes and goes back to that view.

## Picking
- Every game starts with no pick. Tap a team to pick it; tap it again to clear the pick. Points can only be
  set on a picked game.
- A game with no pick is a skip (−20) only once it kicks off. Before that it's just open.

## Email
- The Email tab builds the email from your **saved** picks only, in sheet order with the sheet's team names.
  If you have unsaved changes it says so and offers a Save button.
- Picks on games that already kicked off are left out by default (they went in an earlier email, e.g.
  Thursday's), and the header becomes "Rest of week N." A checkbox adds them back.
- Thursday flow: pick the Thursday game, Save, copy the email. Sunday: pick the rest, Save, copy again.
- Older saves that used Email/Sent/Skip still load: Email and Sent picks keep their team, Skip becomes no pick.

## Scoring (computed by the backend from ESPN final scores)
- A pick wins if that side covers the **sheet** spread (not the live line). A push earns half the points (2½ for a 5).
- Weekly score = points on covered picks + half points on pushes − penalties + manual adjustment.
- Automatic penalties: over 100 (−20 per 10 over), exactly four double-digit picks (−20), skipped games (−20 each).
- Late-pick penalties, out-of-order picks, etc. are entered by hand in the week's **Adjustment** field.
- Final results are cached in the database, so past weeks still score if ESPN is unreachable.

## Season stats
Total, weekly average, record vs spread, best/worst week, points earned vs wagered, cover rate by confidence tier,
favorite/underdog and home/away tendencies, Lock of the Year result, biggest hit/miss, running total.
