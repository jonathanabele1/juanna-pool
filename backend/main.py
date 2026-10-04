"""API for the pool site: login, lines/results (ESPN), each user's saved weeks, scoring and season stats.
Also serves the built frontend (dist/) so the whole site runs as one service."""
import os
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import admin, auth, db, deadlines, espn, scoring
from .weeks import deadline_info, results_for, scored, user_week, user_weeks

app = FastAPI()
app.include_router(auth.router)
app.include_router(admin.router)
auth.bootstrap_admin()

MAX_IMAGE = 10 * 1024 * 1024


class Game(BaseModel, extra="allow"):
    fav: str
    dog: str
    status: Literal["email", "sent", "skip"] = "email"
    pick: Literal["fav", "dog"] = "fav"
    points: int = 2


class WeekIn(BaseModel):
    label: str = ""
    games: list[Game]
    adjustment: int = 0
    adjNote: str = ""


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/lines")
def lines(week: int | None = None, user: dict = Depends(auth.current_user)):
    return espn.fetch_week(week)


@app.get("/api/deadlines")
def week_deadlines(week: int | None = None, user: dict = Depends(auth.current_user)):
    if week is None:
        try:
            week = espn.fetch_week()["week"]
        except HTTPException:
            return {"week": None, "groups": []}
        groups = deadline_info(week)["groups"]
        if groups and all(deadlines.is_past(g["deadline"]) for g in groups) and week < 18:
            week += 1  # everything this week is due already: count down to next week's picks
    return {"week": week, "groups": deadline_info(week)["groups"]}


@app.get("/api/announcement")
def announcement(user: dict = Depends(auth.current_user)):
    return {"text": db.get_setting("announcement")}


@app.get("/api/weeks")
def weeks(user: dict = Depends(auth.current_user)):
    out = []
    for w, games, p in user_weeks(user["id"]):
        s = scored(w["week"], games, p["adjustment"])
        out.append({"week": w["week"], "score": s["score"], "complete": s["complete"],
                    "wins": s["wins"], "losses": s["losses"], "pushes": s["pushes"]})
    return out


@app.get("/api/weeks/{n}")
def get_week(n: int, user: dict = Depends(auth.current_user)):
    return user_week(user["id"], n)


@app.put("/api/weeks/{n}")
def put_week(n: int, body: WeekIn, user: dict = Depends(auth.current_user)):
    posted = [g.model_dump() for g in body.games]
    if user["isAdmin"]:
        db.save_lines(n, posted)  # the admin's sheet is everyone's sheet
    w = db.get_week(n)
    if not w or not w["games"]:
        raise HTTPException(400, "This week's lines aren't posted yet")

    by_key = {db.game_key(g): g for g in posted}
    picks = {key: {k: by_key[key][k] for k in db.USER_FIELDS}
             for key in (db.game_key(g) for g in w["games"]) if key in by_key}
    if user["isAdmin"]:
        db.save_picks(user["id"], n, picks, body.label, body.adjustment, body.adjNote)
    else:
        db.save_picks(user["id"], n, picks, body.label)
    return user_week(user["id"], n)


@app.delete("/api/weeks/{n}")
def delete_my_picks(n: int, user: dict = Depends(auth.current_user)):
    db.delete_picks(user["id"], n)
    return {"ok": True}


@app.put("/api/weeks/{n}/image")
async def put_image(n: int, request: Request, user: dict = Depends(auth.admin_user)):
    ctype = request.headers.get("content-type", "image/png")
    if not ctype.startswith("image/"):
        raise HTTPException(400, "Not an image")
    data = await request.body()
    if len(data) > MAX_IMAGE:
        raise HTTPException(413, "Image is over 10 MB")
    db.set_image(n, data, ctype)
    return {"ok": True}


@app.get("/api/weeks/{n}/image")
def get_image(n: int, user: dict = Depends(auth.current_user)):
    img = db.get_image(n)
    if not img:
        raise HTTPException(404, "No image")
    return Response(img[0], media_type=img[1])


@app.get("/api/stats")
def stats(user: dict = Depends(auth.current_user)):
    rows = user_weeks(user["id"])
    scored_weeks = [(w["week"], scoring.score_week({"week": w["week"], "games": games, "adjustment": p["adjustment"]},
                                                   results_for(w["week"]))) for w, games, p in rows]
    out = scoring.season_stats(scored_weeks)
    out["teams"] = scoring.team_stats([{"week": w["week"], "games": g} for w, g, _ in rows],
                                      db.get_results(), db.get_teams())
    return out


@app.get("/api/teams")
def team_covers(before_week: int | None = None, user: dict = Depends(auth.current_user)):
    """Compact cover (ATS) record per team from your saved sheets, optionally only weeks before `before_week`."""
    weeks_ = [{"week": w["week"], "games": g} for w, g, _ in user_weeks(user["id"])]
    rows = scoring.team_stats(weeks_, db.get_results(), {}, before_week)
    return {r["abbr"]: r["ats"] for r in rows}


# ---- the built Vue app (npm run build) ----
DIST = Path(os.environ.get("POOL_DIST_DIR") or Path(__file__).parent.parent / "dist")
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="site")
