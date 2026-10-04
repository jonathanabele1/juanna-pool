# Strategy: How to Spread Your 100 Points

A look at the math behind the pool's scoring rules ([picks-and-scoring.md](picks-and-scoring.md),
[penalties.md](penalties.md), [prizes.md](prizes.md)), checked with Monte Carlo simulation
([strategy_sim.py](strategy_sim.py), run it with `python3 docs/strategy_sim.py`).

---

## TL;DR

1. **If you can't beat the spread, how you spread your points doesn't change your expected score.** Every
   valid allocation averages **50 points a week** when each pick is a 50/50 coin flip. Point allocation
   only changes **variance** (how much your score swings).
2. **The prizes reward variance.** The weekly prize goes to the top score only, and the year-end payout is
   tilted toward 1st place, so a high-variance allocation wins more money even with no skill. In a
   31-person pool, putting most of your points on a few games wins the week about **1.7–1.9×** as often
   as a fair share. A flat allocation wins it about **0.4×** as often.
3. **Your real edge is the stale Wednesday line.** The sheet spread is locked on Wednesday, but you
   submit on Sunday. When the market line has moved since then, the sheet line is mispriced, and that's
   where your 20s belong. Each half point of movement is worth about 1.5% in cover probability, and
   more when the move crosses 3 or 7.
4. **Watch out for the "exactly 4 double digits" rule.** It hits the most natural maximum-concentration
   allocation in most weeks (for example 20/20/20/16). Use 20-20-20-9-9 or 20-20-18-10-10 instead.
5. **Avoid big points on whole-number spreads (−3, −7).** A push scores 0, the same as a loss.
6. Your current style (three 20s with the rest near the minimum) is already close to optimal. The
   improvements are: choose the 20s by line movement, avoid pushable numbers, and use the LOY on purpose.

---

## 1. The game in one equation

For a week with *n* games, you pick a side and a point value `pᵢ` for each game:

```
score = Σ pᵢ · Xᵢ        Xᵢ = 1 if your side covers, 0 otherwise (push = 0)
subject to   2 ≤ pᵢ ≤ 20 (or one 50 per season),   Σ pᵢ = 100,   #{pᵢ ≥ 10} ≠ 4
```

The constraints leave less freedom than it looks like. With 16 games, the 2-point minimum ties up 32
points, so you have only **68 points to place**. Every allocation is just a choice of where those 68
go.

| Games that week | Points tied up by 2-pt minimum | Free points |
|---|---|---|
| 16 | 32 | 68 |
| 15 | 30 | 70 |
| 14 | 28 | 72 |
| 13 | 26 | 74 |

## 2. Expected value: allocation barely matters

Expected value is linear, so:

```
E[score] = Σ pᵢ · qᵢ = 50 + Σ pᵢ · (qᵢ − 0.5)
```

where `qᵢ` is the chance that your side covers.

* If every `qᵢ = 0.5`, then **E[score] = 50 no matter how you allocate.** NFL spreads are close to
  efficient, so most picks really are near 50%.
* Allocation only matters through your **edge**, `qᵢ − 0.5`. The best possible case is to put the
  maximum points on your highest-edge games. Even then, the gain is small: three 20s at a real 55% add
  `60 × 0.05 = 3 points/week`, or about 54 points over 18 weeks.
* So the season-total race is mostly decided by **who actually picks better than 50%**, plus luck.
  Point allocation magnifies whatever edge you have (positive or negative). It doesn't create one.

> Your first three graded weeks show this. Week 2 went **5–11** but still scored **49**, because both
> of your 20s hit. Week 3 went **9–7** and scored **47**, because two of the three 20s missed.
> Record barely matters. What matters is which games carried the points.

## 3. Variance: this is where allocation matters

With 50/50 picks, `Var(score) = 0.25 · Σ pᵢ²`. Concentrating points increases `Σ pᵢ²`, which
increases the swings.

| Allocation (16 games) | SD of weekly score | P(score ≥ 70) | P(score ≥ 80) | P(score ≤ 30) |
|---|---|---|---|---|
| Flat: 7,7,7,7 + twelve 6s | 12.5 | 5% | 1% | 5% |
| Moderate ladder: 12,11,10,9,8,8,7,6,6,5,4,4,3,3,2,2 | 13.9 | 8% | 2% | 8% |
| **Your style:** 20,20,20 + 40 spread over 13 | 18.3 | 14% | 7% | 14% |
| Max: 20,20,20,9,9 + eleven 2s | 18.7 | 16% | 6% | 16% |
| Max, 5 DD: 20,20,18,10,10 + eleven 2s | 18.5 | 16% | 6% | 16% |
| LOY week: 50,20,4 + thirteen 2s | 27.2 | 29% | 23% | 29% |

Every row averages 50. The difference is only how often you land in the tails.

## 4. The double-digit trap

The rule against **exactly four** picks of 10 or more lands right on the most natural maximum
allocation in most weeks:

| Games | "Greedy" max allocation | DD count | Best legal alternatives |
|---|---|---|---|
| 16 | 20,20,20,**16**, rest 2 | 4 ❌ | 20,20,20,9,9 (3 DD), or 20,20,18,10,10 (5 DD) |
| 15 | 20,20,20,**18**, rest 2 | 4 ❌ | 20,20,20,10,10 (5 DD, uses all 70 exactly) |
| 14 | 20,20,20,**20**, rest 2 | 4 ❌ | 20,20,20,11,11 or 20,20,20,12,10 (5 DD); 20,20,20,9,9,6 (3 DD) |
| 13 | 20,20,20,20,**4**, rest 2 | 4 ❌ | 20,20,20,12,10 (5 DD) |
| 16 + LOY | 50,20,4, rest 2 | 2 ✅ | 50,10,10,4 (3 DD) |

The 4th through 6th picks hold little EV either way, so choose based on the DD count. The penalty
costs 20 points, which is far more than any marginal EV you'd gain. (The LOY is assumed to count as a
double digit; see [open-questions.md](open-questions.md).)

Also note that a **skipped game counts as a used double-digit slot**, so recount when you miss a
Thursday game.

## 5. Weekly prize: variance wins money

The weekly prize goes **only to the top score**. Beating a field of N people is a tail event, so a
high-variance entry wins much more often. In the simulation, each player picks the consensus side 70%
of the time, the outcomes are coin flips, and the field mixes styles (25% flat, 35% ladder, 25% 3×20,
15% max).

**Share of weekly prizes won, as a multiple of a fair 1/(N+1) share:**

| Your allocation | Field of 15 | Field of 30 | Field of 50 |
|---|---|---|---|
| Flat | 0.58× | 0.38× | 0.25× |
| Moderate ladder | 0.75× | 0.61× | 0.53× |
| Your style (3×20) | 1.49× | 1.67× | 1.92× |
| Max (20,20,20,9,9) | 1.54× | 1.85× | 2.15× |
| LOY week (50,20,4) | 3.65× | 5.28× | 6.72× |

* **The bigger the pool, the more variance pays.** Flat players almost never win a week.
* **It's relative to the field:**

  | Field is... | Max allocation | Flat allocation | LOY week |
  |---|---|---|---|
  | All flat | 3.4× | 0.97× | 8.0× |
  | All 3×20 / max | 1.04× | 0.19× | 3.4× |

  Concentrating never hurts. It only stops helping once everyone else does it too.
* **Contrarian ranking** means putting your big points on games the field isn't loading up on (same
  side, different games). It adds about another 5–10% relative win rate. It's a small boost, and it
  costs nothing in EV when you have no strong opinion.
* In dollars (31 players, $77.50 pot): fair is about $2.50/week. Max is about $4.65/week. Flat is about
  $0.95/week.

## 6. Season standings: variance still helps (with zero skill)

The year-end payout is top 10 of N, weighted 21/17/14/11/9/7/6/5/4/3%. That shape is **convex**, so
first place pays seven times what 10th does. In an 18-week simulation against 30 others:

| Your allocation | Edge on your top-5 games | E[share of year-end pot] | P(1st) | P(top 10) |
|---|---|---|---|---|
| Flat | none (50%) | 2.37% | 1.1% | 29% |
| Moderate | none | 2.57% | 1.8% | 30% |
| Your style | none | 3.75% | 5.1% | 35% |
| Max | none | 3.86% | 5.9% | 36% |
| Flat | 53% | 4.25% | 4.5% | 43% |
| Max | 53% | 7.49% | 16.7% | 56% |
| Flat | 55% | 5.18% | 6.4% | 50% |
| Max | 55% | 9.93% | 26.9% | 69% |

(A fair share is 1/31 ≈ 3.23%.)

* With **no edge**, concentrating still beats a fair share, and flat falls below it.
* With **a real edge**, concentrating roughly **doubles** the value of that edge, because more of
  your points sit on the games where you're right.
* This changes late in the season. If you're **leading** with a few weeks left, lowering variance
  protects your spot. If you're **behind**, increase variance (LOY, max concentration, contrarian
  picks).

## 7. Where real edge comes from

### a) The stale Wednesday line (the big one)

The pool scores against the **sheet** spread (bet365, set Wednesday). You submit on Sunday at noon.
By then, injuries, weather, and sharp money have moved the market. If the market moved toward the
favorite (−3.5 → −5.5), the favorite at −3.5 is underpriced. If it moved away, take the dog.

Using a simple normal model of NFL margins (σ ≈ 13.5), here's the cover probability on the sheet line
when the current market is *d* points better for your side:

| Line moved by | Cover prob. | Edge |
|---|---|---|
| 0.5 | 51.5% | +1.5% |
| 1.0 | 53.0% | +3.0% |
| 1.5 | 54.4% | +4.4% |
| 2.0 | 55.9% | +5.9% |
| 3.0 | 58.8% | +8.8% |

Moves that **cross 3 or 7** are worth more than this table shows, because so many NFL games end on
exactly those margins. For example, a sheet line of 2.5 when the market is 3.5 is a better spot than
an ordinary one-point move.

**The app already shows this.** `currentLine()` in `src/lines.js` compares the live ESPN/DraftKings
line with the sheet and flags the delta, including favorite flips. Sort by that delta and put your
20s on the biggest moves in your favor. This is the most reliable way to push `qᵢ` above 50%.

Thursday games have the least time for the line to move (Wed → Thu), so they're usually the worst
place for big points. Sunday and Monday games have had four or more days to move.

### b) Avoid pushable spreads with big points

A push scores 0, the same as a loss. On whole-number spreads, a push is fairly common: very roughly
**8–10% of games lined at 3** and **5–6% at 7** land exactly on the number. That cuts a "50/50"
pick to about 45–47% win / 0 points otherwise. Half-point spreads (2.5, 3.5, 6.5, 7.5) never push.

In week 3, all three of your 20s were on whole numbers (SEA −7, JAX −3, NO −3). Your week 4 20s are
all on half points (WSH +3.5, BUF −6.5, GB −3.5).

### c) Your own track record

The Stats page has cover rates by confidence tier, favorite/dog, and home/away. After 4–6 weeks,
check whether your 20s actually cover more often than your 2s. If they don't, your "confidence"
doesn't carry information, and you should pick your 20s from line movement alone.

## 8. Lock of the Year (50 points, once)

* In EV terms, the LOY is **just more concentration**. At 50% it still averages 50. It's worth
  `50 × edge`, so use it on a game with a large, clear line move (2+ points, ideally through 3). At a
  3-point move (~59%), it's worth about +4.4 points over a coin flip.
* It is the **biggest variance tool in the game**: weekly SD 27, and a 17% chance to win the week in
  a 31-person pool (about 5× a fair share).
* When to use it:
  * **Never sit on it out of fear.** An unused LOY is wasted value.
  * If you're **behind or mid-pack** late in the season, use it to swing.
  * If you're **leading** late, use it only on a big edge, or not at all. It's optional.
  * A 50 makes your other 15 picks very small (20 free points), so the week's result is basically
    "did the LOY hit?"

## 9. Penalties are never worth taking

| Temptation | Why not |
|---|---|
| Go to 110 for 10 extra points | +10 pts × 50% = +5 EV vs −20 penalty |
| Exactly four double digits | −20 for no benefit; a legal alternative always exists |
| Skip a game you hate | −20, and it still uses a DD slot. Put 2 points on it instead. |
| Submit under 100 | No point penalty, but less EV and no carp eligibility. Pure loss. |
| Submit late | Penalty ladder plus lost carp eligibility. Use Thursday's separate submission. |

## 10. Your season so far

| Week | Score | Record | Your 20s |
|---|---|---|---|
| 1 | 56 | 8–8 | JAX −8.5 ✅, PIT −3.5 ✅, DET −6.5 ❌ |
| 2 | 49 | 5–11 | CHI −5.5 ❌, HOU +2.5 ✅, DAL −3.5 ✅ |
| 3 | 47 | 9–7 | SEA −7 ❌, JAX −3 ✅, NO −3 ❌ |
| 4 | pending | — | WSH +3.5, BUF −6.5, GB −3.5 |

You're 5–4 on 20-point picks and averaging 50.7, which is right on the zero-edge expectation. Your
structure (three 20s, everything else near the minimum, 3 double digits) is already in the
high-variance group that the prizes reward.

## 11. Playbook

1. **Every week:** start everything at 2, then place your 68 free points.
2. **Pick your three 20s** using the largest favorable line moves since Wednesday (the app's delta
   column), preferring Sunday/Monday games and half-point spreads.
3. **Remaining points:** go to 9,9 (3 DD) or rework to 20,20,18,10,10 (5 DD). **Never land on 4
   double digits.** Recount if you skipped or defaulted a game.
4. **When you have no edge:** keep the concentrated shape anyway, and put the big points on games
   the field is probably *not* loading up on.
5. **LOY:** save it for a 2+ point favorable move, especially one through 3, or use it as a swing
   if you're behind after about week 12.
6. **Late season:** if you're leading the standings, flatten a bit (e.g. the moderate ladder). If
   you're chasing, go max plus contrarian.
7. **Never** go over 100, skip a game, or submit late.

---

### Assumptions and limits of the simulation

* Outcomes are modeled as independent 50/50 coin flips with half-point spreads (no pushes) unless
  stated otherwise.
* The field's styles and its 70% "consensus side" agreement are guesses. The direction of every
  conclusion held under all field mixes tested, but the exact multiples depend on how your league
  actually plays.
* "Edge" scenarios give you a fixed cover rate on your top 5 games. Real edge varies week to week.
* The line-movement table uses a normal approximation. Real NFL margins cluster on 3 and 7, so moves
  through those numbers are worth more than shown and moves elsewhere slightly less.
* Penalty interpretations follow [open-questions.md](open-questions.md) (LOY counts toward 100 and as
  a double digit).
