"""A user's view of a week: the shared lines merged with their own picks, plus deadline locks and scoring."""
from datetime import datetime, timezone

from fastapi import HTTPException

from . import db, deadlines, espn, scoring

DEFAULT_PICK = {"pick": None, "points": 2}


def _mine(saved: dict | None) -> dict:
    """A stored pick. Older saves carry a status: "skip" meant no pick; "email"/"sent" were both real picks."""
    if not saved:
        return {}
    out = {k: v for k, v in saved.items() if k != "status"}
    if saved.get("status") == "skip":
        out["pick"] = None
    return out


def results_for(week: int) -> dict:
    try:
        espn.fetch_week(week)  # refreshes persisted results + kickoffs; offline falls back to the DB copy
    except HTTPException:
        pass
    return db.get_results()


def deadline_info(n: int, w: dict | None = None) -> dict:
    results_for(n)
    w = w if w is not None else db.get_week(n)
    # the results cache can hold preseason/last-postseason games under the same week number
    season = {eid: k for eid, k in db.kickoffs(n).items() if k >= f"{espn.SEASON}-09-01"}
    return deadlines.compute(season, (w or {}).get("deadlines"))


def merge(lines: list[dict], p: dict | None, info: dict, only_saved: bool = False) -> list[dict]:
    """Each sheet game with this user's pick. Deadlines are reminders only: nothing locks.
    Games without a pick have pick=None (scoring counts them as skipped once they kick off)."""
    now = datetime.now(timezone.utc)
    stored = (p or {}).get("picks", {})
    out = []
    for g in lines:
        dl = deadlines.deadline_for(g, info)
        mine = _mine(stored.get(db.game_key(g)))
        out.append({**g, **DEFAULT_PICK, **mine, "deadline": dl, "pastDue": deadlines.is_past(dl, now)})
    return out


def has_picks(p: dict | None) -> bool:
    return bool(p and p["picks"])


def scored(n: int, games: list[dict], adjustment: int) -> dict:
    s = scoring.score_week({"week": n, "games": games, "adjustment": adjustment}, results_for(n))
    s.pop("_picked", None)
    return s


def user_week(user_id: int, n: int) -> dict:
    w = db.get_week(n)
    p = db.get_picks(user_id, n)
    info = deadline_info(n, w)
    base = {"week": n, "hasImage": bool(w and w["hasImage"]), "imageVersion": w["updatedAt"] if w else None,
            "deadlines": info["groups"]}
    if not w or not w["games"]:
        return {**base, "saved": False, "picksSaved": False}
    games = merge(w["games"], p, info)
    saved = has_picks(p)
    adjustment = p["adjustment"] if p else 0
    return {
        **base,
        "saved": True,
        "picksSaved": saved,
        "games": games,
        "label": p["label"] if p else "",
        "adjustment": adjustment,
        "adjNote": p["adjNote"] if p else "",
        "updatedAt": p["updatedAt"] if saved else None,
        "score": scored(n, games, adjustment) if saved else None,
    }


def in_league(u: dict, viewer_id: int | None) -> bool:
    """Hidden accounts (tests) are left out of the league for everyone but themselves."""
    return not u["hidden"] or u["id"] == viewer_id


def week_entries(n: int, viewer_id: int | None = None) -> tuple[dict | None, dict, list[dict]]:
    """(week lines, results, every player with saved picks: {user, games, picks, score}) scored in one pass.
    Hidden accounts are left out, unless it's the viewer's own.
    The scores keep `_picked` (for season stats): don't return them to the browser as-is."""
    w = db.get_week(n)
    if not w or not w["games"]:
        return w, {}, []
    info = deadline_info(n, w)  # also refreshes the week's results
    results = db.get_results()
    users = {u["id"]: u for u in db.list_users()}
    out = []
    for uid, p in db.week_picks(n).items():
        if uid not in users or not has_picks(p) or not in_league(users[uid], viewer_id):
            continue
        games = merge(w["games"], p, info)
        s = scoring.score_week({"week": n, "games": games, "adjustment": p["adjustment"]}, results)
        out.append({"user": users[uid], "games": games, "picks": p, "score": s})
    return w, results, out


def started(g: dict, results: dict, week_games: list[dict]) -> bool:
    """Has this game kicked off? Games we couldn't match to ESPN count once every matched game is final."""
    res = results.get(str(g.get("eventId") or ""))
    if res:
        return res["state"] in ("in", "post")
    known = [results.get(str(x.get("eventId") or "")) for x in week_games]
    known = [r for r in known if r]
    return bool(known) and all(r["state"] == "post" for r in known)


def user_weeks(user_id: int) -> list[tuple[dict, list[dict], dict]]:
    """(week lines, merged saved games, picks row) for every week this user has picks on."""
    mine = db.user_picks(user_id)
    out = []
    for w in db.list_weeks():
        p = mine.get(w["week"])
        if w["games"] and has_picks(p):
            out.append((w, merge(w["games"], p, deadline_info(w["week"], w), only_saved=True), p))
    return out


def week_summaries(user_id: int) -> list[dict]:
    """Score + record for each week a user has picks on (the week bar)."""
    out = []
    for w, games, p in user_weeks(user_id):
        s = scored(w["week"], games, p["adjustment"])
        out.append({"week": w["week"], "score": s["score"], "complete": s["complete"],
                    "wins": s["wins"], "losses": s["losses"], "pushes": s["pushes"],
                    "live": sum(s["live"][k] for k in ("wins", "losses", "pushes")) > 0})
    return out


def season(user_id: int) -> dict:
    rows = user_weeks(user_id)
    scored_weeks = [(w["week"], scoring.score_week({"week": w["week"], "games": games, "adjustment": p["adjustment"]},
                                                   results_for(w["week"]))) for w, games, p in rows]
    out = scoring.season_stats(scored_weeks)
    out["teams"] = scoring.team_stats([{"week": w["week"], "games": g} for w, g, _ in rows],
                                      db.get_results(), db.get_teams())
    return out
