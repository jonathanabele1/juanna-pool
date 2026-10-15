"""Admin-only "test live mode": fake scores for this week's games (and later weeks; finished weeks stay real), to see what game day looks like.

An admin's browser sends `X-Demo-Live: 1`; for that request only, the scoreboard reports ~40% of the week's games
final, ~30% live (moving along every 30s: a live game runs Q1 to the 4th quarter in 30 minutes, then starts over)
and the rest not started. Nothing fake is ever saved or shown to anyone else.

Other players' picks on games that haven't *really* kicked off are swapped for made-up picks while the mode is on,
so it can't be used to peek at hidden picks.
"""
import copy
import hashlib
import random
import time
from contextvars import ContextVar
from http.cookies import SimpleCookie

HEADER = b"x-demo-live"
CYCLE = 30 * 60

viewer: ContextVar[int | None] = ContextVar("demo_viewer", default=None)  # the admin, while the mode is on
_fake: dict[str, dict] = {}  # event id -> fake results row, from the last demo scoreboard


def active() -> bool:
    return viewer.get() is not None


def _rng(*parts) -> random.Random:
    return random.Random(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest())


def _plays(eid: str) -> list[tuple[float, str, int]]:
    """A game's scoring plays: (when, 0..1 of the game; side; points)."""
    r = _rng("plays", eid)
    return sorted((r.random(), r.choice(("home", "away")), r.choice((3, 3, 7, 7, 7, 6))) for _ in range(r.randint(5, 11)))


def _score(eid: str, p: float) -> dict:
    s = {"home": 0, "away": 0}
    for t, side, pts in _plays(eid):
        if t <= p:
            s[side] += pts
    return s


LAST_PLAYS = ["Pass complete short right for 8 yards", "Run up the middle for 3 yards", "Incomplete deep left",
              "Sacked for a loss of 6", "Run off left tackle for 12 yards", "Pass complete deep middle for 24 yards",
              "Penalty: holding, 10 yards", "Timeout #1"]


def _live(e: dict, i: int, p: float, now: float) -> dict:
    q = min(4, int(p * 4) + 1)
    left = int((1 - (p * 4 - (q - 1))) * 900)
    r = _rng("drive", e["id"], int(now // 30))
    has, other = (e["home"], e["away"]) if r.random() < .5 else (e["away"], e["home"])
    yard = r.randint(4, 45)
    down = r.randint(1, 4)
    return {
        "period": q, "quarter": f"Q{q}", "clock": f"{left // 60}:{left % 60:02d}",
        "halftime": False, "endOfPeriod": False, "possession": has["abbr"],
        "down": f"{down}{['st', 'nd', 'rd', 'th'][down - 1]} & {r.randint(1, 10)}",
        "spot": f"{other['abbr']} {yard}", "redZone": yard <= 20, "lastPlay": r.choice(LAST_PLAYS),
    }


def scoreboard(data: dict) -> dict:
    """A week's real scoreboard with fake states and scores (a copy; the real one is untouched)."""
    data = copy.deepcopy(data)
    evs = sorted(data["events"], key=lambda e: e["kickoff"])
    n = len(evs)
    final_n, live_n = (n * 4) // 10, max(1, (n * 3) // 10)
    now = time.time()
    for i, e in enumerate(evs):
        if i < final_n:
            e.update(state="post", detail="Final", live=None, scores=_score(e["id"], 1))
        elif i < final_n + live_n:
            # stagger the live games so they're in different quarters
            p = min(.97, max(.03, ((now + (i - final_n) * CYCLE / live_n) % CYCLE) / CYCLE))
            e.update(state="in", detail="", scores=_score(e["id"], p), live=_live(e, i, p, now))
        else:
            e.update(state="pre", live=None, scores={"home": None, "away": None})
        _fake[e["id"]] = {"event_id": e["id"], "week": data["week"], "state": e["state"],
                          "home_abbr": e["home"]["abbr"], "away_abbr": e["away"]["abbr"],
                          "home_score": e["scores"]["home"], "away_score": e["scores"]["away"],
                          "kickoff": e["kickoff"]}
    data["demo"] = True
    return data


def results(real: dict[str, dict]) -> dict[str, dict]:
    return {**real, **_fake} if active() else real


def picks(user_id: int, stored: dict, real_results: dict[str, dict]) -> dict:
    """Someone else's picks, with a made-up pick on every game that hasn't really kicked off."""
    if not active() or user_id == viewer.get():
        return stored
    out = {}
    for key, pick in stored.items():
        res = real_results.get(key[3:]) if key.startswith("ev:") else None
        if res and res["state"] in ("in", "post"):
            out[key] = pick
        else:
            r = _rng("pick", user_id, key)
            out[key] = {"pick": r.choice(("fav", "dog")), "points": r.choice((2, 3, 4, 5, 6, 8, 10, 12, 15))}
    return out


class Middleware:
    """Turns the mode on for a request carrying the header, if it comes from a signed-in admin."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            # the admin tab always shows the real thing
            if headers.get(HEADER) == b"1" and not scope["path"].startswith("/api/admin"):
                from . import auth, db
                cookie = SimpleCookie(headers.get(b"cookie", b"").decode("latin-1")).get(auth.COOKIE)
                user = db.session_user(auth._token_hash(cookie.value)) if cookie else None
                if user and user["isAdmin"]:
                    token = viewer.set(user["id"])
                    try:
                        return await self.app(scope, receive, send)
                    finally:
                        viewer.reset(token)
        await self.app(scope, receive, send)
