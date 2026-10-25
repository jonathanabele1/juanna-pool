"""Chance a side covers, from the score, the clock and who has the ball.

The odds come from a table of how NFL margins actually moved over the rest of a game (cover_table.json, built from
nflverse play-by-play by scripts/build_cover_table.py). For each spot (time left, current margin, field position of the
team with the ball) it holds how often the margin changed by each amount by the final whistle. Real scores, so the 3s
and 7s, kneel-downs and pushes come out right. Within a cell the odds are reweighted toward the market's line for this
game (a 7-point favorite gains more over the rest of a game than a 4-point one).
"""
import json
import math
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path

TABLE = Path(__file__).with_name("cover_table.json")
GAME = 3600
OWN_25 = 75  # where a drive usually starts, for when nobody has the ball (halftime, between scores)


@lru_cache(maxsize=1)
def _table() -> dict:
    t = json.loads(TABLE.read_text())
    for c in t["cells"].values():
        c["d"] = [(int(k), p) for k, p in c["d"].items()]
    return t


def _bin(edges: list, x: float) -> int:
    return bisect_right(edges, x)


def keys(tb: str, mb, fb, zb) -> list[str]:
    """Cells that could answer for a spot, finest first: exact field position, then a coarser field zone, then any.
    A cell is in the table only when enough games went through it."""
    return [f"{tb}|{mb}|{fb}", f"{tb}|{mb}|{zb}", f"{tb}|{mb}|*", f"{tb}|*|{fb}", f"{tb}|*|*"]


def _cell(seconds_left: float, ot: bool, pos_margin: int, yardline: float) -> dict:
    t = _table()
    tb = f"o{_bin(t['otEdges'], seconds_left)}" if ot else f"r{_bin(t['timeEdges'], seconds_left)}"
    for key in keys(tb, _bin(t["marginEdges"], pos_margin), _bin(t["fieldEdges"], yardline),
                    f"z{_bin(t['zoneEdges'], yardline)}"):
        if key in t["cells"]:
            return t["cells"][key]
    raise KeyError(tb)


def _tilt(dist: list, target: float) -> list:
    """Reweight a distribution (p_k ∝ p_k·e^(λk)) so its mean is `target`, keeping where the mass sits (3s, 7s)."""
    def shifted(lam):
        w = [(k, p * math.exp(lam * k)) for k, p in dist]
        s = sum(p for _, p in w)
        return [(k, p / s) for k, p in w]

    mean = lambda d: sum(k * p for k, p in d)
    lo, hi = -1.0, 1.0
    if not (mean(shifted(lo)) <= target <= mean(shifted(hi))):
        return shifted(lo if target < mean(dist) else hi)
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if mean(shifted(mid)) < target else (lo, mid)
    return shifted((lo + hi) / 2)


def _changes(seconds_left: float, ot: bool, margin: int, has_ball: bool, yardline: float, expected: float) -> list:
    """How the side's margin changes from here to the end: [(change, prob)]."""
    sign = 1 if has_ball else -1  # the table is from the point of view of the team with the ball
    c = _cell(seconds_left, ot, sign * margin, yardline)
    target = c["md"] + _table()["beta"] * (sign * expected - c["ms"]) * min(seconds_left, GAME) / GAME
    return [(sign * k, p) for k, p in _tilt(c["d"], target)]


def _odds(margin, need, seconds_left, ot, has_ball, yardline, expected) -> tuple[float, float]:
    """(cover, push)."""
    if has_ball is None or yardline is None:
        changes = [(k, p / 2) for hb in (True, False) for k, p in _changes(seconds_left, ot, margin, hb, OWN_25, expected)]
    else:
        changes = _changes(seconds_left, ot, margin, has_ball, yardline, expected)
    return sum(p for k, p in changes if margin + k > need), sum(p for k, p in changes if margin + k == need)


@lru_cache(maxsize=256)
def _fair(line: float) -> float:
    """The expected margin at which `line` is an even bet at kickoff. A market line is the margin each side is as
    likely to beat as not (the median), not the average margin, and with real scores the two differ a little."""
    lo, hi = line - 3, line + 3
    for _ in range(30):
        mid = (lo + hi) / 2
        cover, push = _odds(0, line, GAME, False, None, None, mid)
        lo, hi = (mid, hi) if cover < 1 - cover - push else (lo, mid)
    return (lo + hi) / 2


@lru_cache(maxsize=4096)  # every player's pick on a game asks the same question
def odds(margin: int, need: float, seconds_left: float, *, ot: bool = False, has_ball: bool | None = None,
         yardline: float | None = None, expected: float = 0.0) -> dict:
    """Chance a side ends up covering, pushing or missing.

    margin: the side's lead right now (negative when behind). need: the side covers if its final margin is more than
    this (3.5 for a favorite laying 3.5, -3.5 for the dog getting 3.5). seconds_left: on the game clock (OT: on the OT
    clock). has_ball: whether this side has the ball (None when nobody does). yardline: yards from the opponent's end
    zone for whoever has the ball. expected: the market's line for the side, as a margin (3.5 when it's favored by
    3.5, -3.5 as the dog). At kickoff, a side whose `need` matches the market line is an even bet.
    The result is cached and shared: don't change it.
    """
    cover, push = _odds(margin, need, seconds_left, ot, has_ball, yardline, _fair(expected))
    return {"cover": cover, "push": push, "miss": max(0.0, 1 - cover - push)}
