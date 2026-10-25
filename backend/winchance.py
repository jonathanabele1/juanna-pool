"""Each player's chance to win the week (top score among the players here; record breaks a tie, then it's split).

The rest of the week is played out a few thousand times. A game on now ends by its cover odds (cover.py), and every
player's pick on it pays off from that same result, so players on the same side rise and fall together.

Games that haven't kicked off are different: their picks are hidden, and the odds mustn't give them away (you could
save different picks and watch your chances move). So no one's actual picks on them are used. Each player's points
on those games (the total the Max column already shows) are spread evenly over them and each one is a coin flip.
"""
import hashlib
import json
import random
from functools import lru_cache

from . import scoring
from .weeks import started

SIMS = 3000


def chances(lines: list[dict], results: dict, entries: list[dict]) -> dict[int, float] | None:
    """{user id: chance to win} while the week is still being decided, else None."""
    live, unstarted = [], []
    for i, g in enumerate(lines):
        res = results.get(str(g.get("eventId") or ""))
        if res and res["state"] == "post":
            continue
        if started(g, results, lines):
            o = scoring.game_odds(g, results) or {"fav": 0.5, "push": 0.0}
            live.append((i, round(o["fav"], 3), round(o["push"], 3)))
        else:
            unstarted.append(i)
    if not entries or not (live or unstarted):
        return None

    players = []
    for e in entries:
        s, games = e["score"], e["games"]
        pay = []  # per live game, for (favorite covers, push, underdog covers): (points, wins)
        for i, _, _ in live:
            g = games[i]
            pts = int(g.get("points") or 0) if g.get("pick") else 0
            half = scoring.push_points(pts)
            pay.append(((pts, 1), (half, 0), (0, 0)) if g.get("pick") == "fav"
                       else ((0, 0), (half, 0), (pts, 1)) if g.get("pick") == "dog" else ((0, 0),) * 3)
        hidden = sum(int(games[i].get("points") or 0) for i in unstarted if games[i].get("pick"))
        players.append((e["user"]["id"], s["score"], s["wins"], s["maxScore"], tuple(pay), hidden))
    return dict(_simulate(tuple(live), len(unstarted), tuple(players)))


@lru_cache(maxsize=64)  # every viewer polling the same game state shares one run
def _simulate(live: tuple, unstarted: int, players: tuple) -> tuple:
    # same state, same answer: no flicker between refreshes
    rng = random.Random(hashlib.sha256(json.dumps([live, unstarted, players]).encode()).digest())
    won = [0.0] * len(players)
    for _ in range(SIMS):
        outs = []
        for _, fav, push in live:
            x = rng.random()
            outs.append(0 if x < fav else 1 if x < fav + push else 2)
        best, leaders = None, []
        for k, (_, score, wins, _, pay, hidden) in enumerate(players):
            total, w = score, wins
            for j, o in enumerate(outs):
                total += pay[j][o][0]
                w += pay[j][o][1]
            if unstarted and hidden:
                hits = bin(rng.getrandbits(unstarted)).count("1")
                total += hidden * hits / unstarted
                w += hits
            key = (total, w)
            if best is None or key > best:
                best, leaders = key, [k]
            elif key == best:
                leaders.append(k)
        for k in leaders:
            won[k] += 1 / len(leaders)

    out = []
    for k, (uid, score, _, max_score, _, _) in enumerate(players):
        others = [p for j, p in enumerate(players) if j != k]
        if not others:
            p = 1.0
        elif max_score < max(p[1] for p in others):
            p = 0.0  # can't catch the leader even if everything left covers
        elif score > max(p[3] for p in others):
            p = 1.0  # no one can catch them
        else:
            # a simulation can miss a long shot (or a near-lock); only the checks above say never or certain
            p = min(max(won[k] / SIMS, 0.001), 0.999)
        out.append((uid, round(p, 4)))
    return tuple(out)
