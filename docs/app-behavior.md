# App Behavior

## Weeks and persistence
- Everything is stored in one SQLite file, **`backend/data/pool.db`** (`/data/pool.db` on Railway): accounts, each
  week's lines and sheet image, and every player's picks. See [deploy.md](deploy.md) for accounts and backups.
- The week bar (1–18) switches weeks. Saved weeks show their score; the current NFL week is marked "now".
- **Save picks** stores the whole week. **Save & mark as sent** also flips the games in the email to "Sent".
- Re-uploading an image replaces the matchups but keeps your pick/points for any matchup that still exists.
- "Clear my picks" removes your saved picks for that week (not allowed once any of its deadlines have passed).

## Per-game status
| Status | Meaning | In the email? | Counts toward the 100? |
|---|---|---|---|
| Email | Part of the email being written | Yes | Yes |
| Sent | Already emailed earlier (e.g. Thursday) | No | Yes |
| Skip | No pick | No | No (−20 each) |

Mid-week, games that have already kicked off default to "Sent". For a past week, everything defaults to "Email".

## Scoring (computed by the backend from ESPN final scores)
- A pick wins if that side covers the **sheet** spread (not the live line). Push = 0 points.
- Weekly score = points on covered picks − penalties + manual adjustment.
- Automatic penalties: over 100 (−20 per 10 over), exactly four double-digit picks (−20), skipped games (−20 each).
- Late-pick penalties, out-of-order picks, etc. are entered by hand in the week's **Adjustment** field.
- Final results are cached in the database, so past weeks still score if ESPN is unreachable.

## Season stats
Total, weekly average, record vs spread, best/worst week, points earned vs wagered, cover rate by confidence tier,
favorite/underdog and home/away tendencies, Lock of the Year result, biggest hit/miss, running total.
