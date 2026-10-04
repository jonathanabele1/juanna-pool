"""ESPN public scoreboard (carries DraftKings spreads + final scores).

DraftKings' own site blocks automated requests, so we don't hit it directly.
"""
import time

import httpx
from fastapi import HTTPException

from . import db

ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
SEASON = 2026
LIVE_TTL = 60
FINAL_TTL = 3600

_cache: dict = {}  # key (week|None) -> (fetched_at, data)


def _team(c: dict) -> dict:
    t = c["team"]
    return {
        "abbr": t.get("abbreviation", ""),
        "location": t.get("location", ""),
        "name": t.get("name", ""),
        "logo": t.get("logo"),
        "color": t.get("color"),
    }


def _record(c: dict) -> str | None:
    for r in c.get("records") or []:
        if r.get("type") == "total":
            return r.get("summary")
    return None


def _pregame(rec: str | None, result: str) -> str | None:
    """ESPN reports the record *after* a finished game; step back one game to get the record going in."""
    if not rec:
        return rec
    try:
        w, l, *t = [int(x) for x in rec.split("-")]
        t = t[0] if t else 0
        w, l, t = (w - 1, l, t) if result == "w" else (w, l - 1, t) if result == "l" else (w, l, t - 1)
        return f"{w}-{l}" + (f"-{t}" if t else "")
    except ValueError:
        return rec


def _score(c: dict):
    try:
        return int(c.get("score"))
    except (TypeError, ValueError):
        return None


def _event(e: dict) -> dict:
    comp = e["competitions"][0]
    home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
    away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
    odds = (comp.get("odds") or [None])[0]
    line = None
    if odds:
        fav = None
        if odds.get("homeTeamOdds", {}).get("favorite"):
            fav = home["team"]["abbreviation"]
        elif odds.get("awayTeamOdds", {}).get("favorite"):
            fav = away["team"]["abbreviation"]
        line = {
            "provider": (odds.get("provider") or {}).get("name"),
            "favorite": fav,  # None for pick'em
            "spread": abs(float(odds.get("spread") or 0)),
        }
    st = e["status"]["type"]
    hs, as_ = _score(home), _score(away)
    hrec, arec = _record(home), _record(away)
    if st["state"] == "post" and hs is not None and as_ is not None:
        hres, ares = ("w", "l") if hs > as_ else ("l", "w") if hs < as_ else ("t", "t")
        hrec, arec = _pregame(hrec, hres), _pregame(arec, ares)
    return {
        "id": e["id"],
        "kickoff": e["date"],
        "state": st["state"],  # pre | in | post
        "detail": st.get("shortDetail", ""),
        "home": {**_team(home), "record": hrec},
        "away": {**_team(away), "record": arec},
        "scores": {"home": hs, "away": as_},
        "line": line,
    }


def fetch_week(week: int | None = None) -> dict:
    """Events for a week (None = ESPN's current week). Final results are persisted."""
    now = time.time()
    hit = _cache.get(week)
    if hit:
        ttl = FINAL_TTL if all(e["state"] == "post" for e in hit[1]["events"]) else LIVE_TTL
        if now - hit[0] < ttl:
            return hit[1]
    # with no week, ask for the current scoreboard: dates=SEASON alone returns ~100 games across the calendar year
    params = {"dates": SEASON, "seasontype": 2, "week": week} if week else {}
    try:
        r = httpx.get(ESPN, params=params, timeout=15)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Could not reach ESPN: {exc}")
    j = r.json()
    number = (j.get("week") or {}).get("number") or week
    data = {
        "week": number,
        "fetchedAt": int(now * 1000),
        "events": [_event(e) for e in j.get("events", [])],
    }
    _cache[week] = (now, data)
    if number:
        db.save_results(number, data["events"])
    return data
