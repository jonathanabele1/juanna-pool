# Juanna Football Pool (2026) — Rules Reference

Reference docs for building the local pool-management site (Vue frontend, optional Python backend).
Source: commissioner's 2026 memo ("Football Picks, 2026"). Where the memo is ambiguous, see
[open-questions.md](open-questions.md) — those need a decision before we code the affected logic.

| Doc | Contents |
|---|---|
| [overview.md](overview.md) | What the pool is, season shape, entry fee, deadlines for payment |
| [picks-and-scoring.md](picks-and-scoring.md) | Ranking games, point values, LOY, double-digit rule, weekly score |
| [penalties.md](penalties.md) | Every penalty and eligibility loss, as a lookup table |
| [submission.md](submission.md) | Deadlines, lateness, defaults, how picks are submitted, protests |
| [prizes.md](prizes.md) | Weekly prize, year-end payouts, tiebreakers, "carp" award |
| [app-behavior.md](app-behavior.md) | How the built app saves, scores and shows stats |
| [deploy.md](deploy.md) | Logins, admin powers, deadlines, running locally, Railway + custom domain |
| [data-model.md](data-model.md) | Proposed entities/fields derived from the rules |
| [open-questions.md](open-questions.md) | Ambiguities and assumptions to confirm |
| [strategy.md](strategy.md) | Math of point allocation, variance, edge, LOY timing (sim: strategy_sim.py) |

## Glossary

- **Spread / line**: Point spread from bet365 via vegasinsider.com. You pick the side that *covers*.
- **Confidence points**: The value (2–20, or 50 for LOY) assigned to each game pick.
- **LOY**: Lock of the Year — one-time 50-point pick.
- **"Carp" award**: Dubious cash prize to the last-place finisher; requires a perfect-compliance season.
- **Default list / nuclear default**: Pre-registered automatic picks for off-Sunday games.
- **Commissioner**: Runs the pool and posts standings; a few named helpers assist.
