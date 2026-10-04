# Proposed Data Model

Derived from the rules; adjust once [open-questions.md](open-questions.md) is settled.

| Entity | Fields |
|---|---|
| **Participant** | id, name, years_in_pool, fee_paid (bool/date), default_type (`none`/`standard`/`nuclear`), default_pick (team side + points), loy_used_week (nullable) |
| **Week** | number (1–18), start/end dates |
| **Game** | id, week, order_index, away, home, kickoff (ET), spread (bet365), day_type (Wed/Thu/Sun/Mon/other), result (home/away margin) |
| **PickSet** | participant, week, submitted_at, channel, late_minutes, notes |
| **Pick** | pickset, game, team (cover side), points (2–20 or 50), source (`manual`/`default`) |
| **Adjustment** | participant, week, kind, points, note (for manual commissioner penalties, e.g. out-of-order) |
| **Protest** | participant, week, opened_at (2-week window) |

## Derived per week/participant
- total_points_assigned, double_digit_count, games_missing
- late_count (season cumulative), late_penalty
- penalties: over-100, double-digit-4, missing-games, default-mismatch, out-of-order
- covered points, record (W–L), weekly_score
- flags: carp_eligible, weekly_prize_eligible

## Validation to build into pick entry
1. Each point ∈ {2..20} ∪ {50}; 50 only once all season.
2. Sum vs 100 (warn on over/under, show penalty tier).
3. Double-digit count ≠ 4 (warn).
4. All games picked; missing count shown with its −20 each.
5. Picks listed in site order.
6. Deadline: 60 min before first game of that day.

## Proposed app structure
- `docs/` rules (this folder)
- `frontend/` Vue 3 + Vite
- `backend/` Python (FastAPI) + SQLite — only needed for persistence and importing lines/results
