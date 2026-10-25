"""The rest of the pool: other players' picks and stats, standings, the pool's split on each game, public betting.

Another player's pick on a game stays hidden until that game kicks off (for everyone, admins included).
"""
from fastapi import APIRouter, Depends, HTTPException

from . import auth, db, scoring, splits, winchance
from .weeks import in_league, season, started, user_week, week_entries, week_summaries

router = APIRouter(prefix="/api")


def _player(user_id: int, me: dict) -> dict:
    u = db.get_user(user_id)
    if not u or not in_league(u, me["id"]):
        raise HTTPException(404, "No such player")
    return u


def _ranks(rows: list[dict], key: str) -> list[int]:
    """Competition ranking (1, 2, 2, 4) by rows[key], highest first, in the rows' current order."""
    vals = [r[key] for r in rows]
    return [1 + sum(1 for v in vals if v > x) for x in vals]


@router.get("/players")
def players(me: dict = Depends(auth.current_user)):
    return [{"id": u["id"], "displayName": u["displayName"], "me": u["id"] == me["id"]}
            for u in db.list_users() if u["active"] and in_league(u, me["id"])]


@router.get("/players/{user_id}/weeks")
def player_weeks(user_id: int, me: dict = Depends(auth.current_user)):
    _player(user_id, me)
    return week_summaries(user_id)


@router.get("/players/{user_id}/weeks/{n}")
def player_week(user_id: int, n: int, me: dict = Depends(auth.current_user)):
    player = _player(user_id, me)
    out = user_week(user_id, n)
    out["player"] = {"id": player["id"], "displayName": player["displayName"], "me": user_id == me["id"]}
    if user_id == me["id"] or not out.get("games"):
        return out
    results = db.get_results()
    lines = out["games"]
    hidden = 0
    for i, g in enumerate(lines):
        if started(g, results, lines):
            continue
        hidden += 1
        lines[i] = {**g, "pick": None, "points": None, "hidden": True}
        if out.get("score"):
            out["score"]["games"][i] = {"outcome": "hidden"}
    out["hiddenCount"] = hidden
    out.pop("adjNote", None)
    out.pop("label", None)
    return out


@router.get("/players/{user_id}/stats")
def player_stats(user_id: int, me: dict = Depends(auth.current_user)):
    _player(user_id, me)
    return season(user_id)


@router.get("/standings/week/{n}")
def week_standings(n: int, me: dict = Depends(auth.current_user)):
    w, results, entries = week_entries(n, me["id"])
    lines = (w or {}).get("games") or []
    states = [(results.get(str(g.get("eventId") or "")) or {}).get("state") for g in lines]
    win = winchance.chances(lines, results, entries) or {}
    rows = []
    for e in entries:
        s = e["score"]
        rows.append({
            "id": e["user"]["id"], "name": e["user"]["displayName"], "me": e["user"]["id"] == me["id"],
            "score": s["score"], "projected": s["ifEndedNow"], "max": s["maxScore"], "liveMax": s["liveMax"],
            "wins": s["wins"], "losses": s["losses"], "pushes": s["pushes"],
            "live": s["live"], "pending": s["pending"], "complete": s["complete"],
            "penalties": s["penaltyTotal"], "adjustment": s["adjustment"],
            "win": win.get(e["user"]["id"]),  # chance to win the week, while it's still being decided
        })
    rows.sort(key=lambda r: (-r["projected"], -r["score"], r["name"].lower()))
    for r, rank, proj in zip(rows, _ranks(rows, "score"), _ranks(rows, "projected")):
        r["rank"], r["projectedRank"] = rank, proj
    with_picks = {r["id"] for r in rows}
    missing = [u["displayName"] for u in db.list_users()
               if u["active"] and in_league(u, me["id"]) and u["id"] not in with_picks]
    return {
        "week": n, "posted": bool(lines), "rows": rows, "noPicks": missing,
        "games": {"total": len(lines), "live": states.count("in"), "final": states.count("post")},
    }


@router.get("/standings/season")
def season_standings(me: dict = Depends(auth.current_user)):
    per_user: dict[int, list] = {}
    names: dict[int, str] = {}
    weekly_wins: dict[int, int] = {}
    for w in db.list_weeks():
        if not w["games"]:
            continue
        _, results, entries = week_entries(w["week"], me["id"])
        for e in entries:
            per_user.setdefault(e["user"]["id"], []).append((w["week"], e["score"]))
            names[e["user"]["id"]] = e["user"]["displayName"]
        states = [(results.get(str(g.get("eventId") or "")) or {}).get("state") for g in w["games"]]
        if entries and states and all(st == "post" for st in states):  # week is over: who won it
            best = max(e["score"]["score"] for e in entries)
            for e in entries:
                if e["score"]["score"] == best:
                    weekly_wins[e["user"]["id"]] = weekly_wins.get(e["user"]["id"], 0) + 1
    rows = []
    for uid, weeks in per_user.items():
        s = scoring.season_stats(weeks)
        if not s["weeksPlayed"]:
            continue
        rows.append({
            "id": uid, "name": names[uid], "me": uid == me["id"],
            "total": s["total"], "average": s["average"], "weeksPlayed": s["weeksPlayed"],
            "record": s["record"], "best": s["best"], "weeklyWins": weekly_wins.get(uid, 0),
            "penalties": s["penalties"],
            # live: the total if the games on now ended as they stand
            "projected": s["total"] + sum(x["ifEndedNow"] - x["score"] for _, x in weeks),
        })
    rows.sort(key=lambda r: (-r["total"], r["name"].lower()))
    for r, rank in zip(rows, _ranks(rows, "total")):
        r["rank"] = rank
    # where everyone stood before the latest week with results: the table shows places moved since then
    played = {n for weeks in per_user.values() for n, s in weeks if s["wins"] + s["losses"] + s["pushes"]}
    if len(played) > 1:
        latest = max(played)
        for r in rows:
            r["prevTotal"] = r["total"] - sum(s["score"] for n, s in per_user[r["id"]]
                                              if n == latest and s["wins"] + s["losses"] + s["pushes"])
        for r, rank in zip(rows, _ranks(rows, "prevTotal")):
            r["lastRank"] = rank
        for r in rows:
            del r["prevTotal"]
    return {"rows": rows, "latestWeek": max(played) if played else None}


@router.get("/weeks/{n}/pool")
def pool(n: int, me: dict = Depends(auth.current_user)):
    """How the pool picked each game, once it kicks off: counts, points, and every player's pick."""
    w, results, entries = week_entries(n, me["id"])
    lines = (w or {}).get("games") or []
    out = []
    for i, g in enumerate(lines):
        key = db.game_key(g)
        if not started(g, results, lines):
            out.append({"key": key, "revealed": False})
            continue
        picks = []
        for e in entries:
            mg, sg = e["games"][i], e["score"]["games"][i]
            picks.append({
                "id": e["user"]["id"], "name": e["user"]["displayName"], "me": e["user"]["id"] == me["id"],
                "pick": mg.get("pick"), "points": int(mg["points"]) if mg.get("pick") else None,
                "outcome": sg.get("outcome"), "live": sg.get("live"), "earned": sg.get("earned"),
            })
        side = lambda k: {"count": sum(1 for p in picks if p["pick"] == k),
                          "points": sum(p["points"] for p in picks if p["pick"] == k)}
        picks.sort(key=lambda p: (p["pick"] is None, -(p["points"] or 0), p["name"].lower()))
        out.append({"key": key, "revealed": True, "fav": side("fav"), "dog": side("dog"),
                    "none": sum(1 for p in picks if not p["pick"]), "picks": picks})
    return {"week": n, "players": len(entries), "games": out}


@router.get("/splits")
def public_splits(week: int, me: dict = Depends(auth.current_user)):
    """DraftKings public betting on each game's spread: event id -> {sides: {abbr: {bets, handle, line}}}."""
    return splits.for_week(week)
