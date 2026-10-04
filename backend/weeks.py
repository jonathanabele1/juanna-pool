"""A user's view of a week: the shared lines merged with their own picks, plus deadline locks and scoring."""
from datetime import datetime, timezone

from fastapi import HTTPException

from . import db, deadlines, espn, scoring

DEFAULT_PICK = {"status": "email", "pick": "fav", "points": 2}


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
    only_saved: games the user never saved count as skipped (for scoring/stats)."""
    now = datetime.now(timezone.utc)
    stored = (p or {}).get("picks", {})
    out = []
    for g in lines:
        dl = deadlines.deadline_for(g, info)
        mine = stored.get(db.game_key(g))
        if mine is None:
            mine = {"status": "skip"} if only_saved else {}
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


def user_weeks(user_id: int) -> list[tuple[dict, list[dict], dict]]:
    """(week lines, merged saved games, picks row) for every week this user has picks on."""
    mine = db.user_picks(user_id)
    out = []
    for w in db.list_weeks():
        p = mine.get(w["week"])
        if w["games"] and has_picks(p):
            out.append((w, merge(w["games"], p, deadline_info(w["week"], w), only_saved=True), p))
    return out
