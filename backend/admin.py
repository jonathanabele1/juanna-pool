"""Admin-only API: accounts, deadline overrides, per-player adjustments/unlocks, announcement, backup/restore."""
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import auth, db
from .weeks import deadline_info, has_picks, merge, scored

router = APIRouter(prefix="/api/admin", dependencies=[Depends(auth.admin_user)])


class NewUser(BaseModel):
    username: str
    displayName: str = ""
    password: str
    isAdmin: bool = False


class UserPatch(BaseModel):
    displayName: str | None = None
    password: str | None = None
    isAdmin: bool | None = None
    active: bool | None = None


class PickPatch(BaseModel):
    adjustment: int = 0
    adjNote: str = ""
    unlocked: bool = False


class Overrides(BaseModel):
    overrides: dict[str, str | None]  # deadline group id (ET date) -> ISO time, or null to go back to automatic


class Announcement(BaseModel):
    text: str = ""


class Signup(BaseModel):
    open: bool = True
    code: str = ""


# ---------------- users ----------------

@router.get("/users")
def users():
    return db.list_users()


@router.post("/users")
def create_user(body: NewUser):
    username = auth.validate_username(body.username)
    auth.validate_password(body.password)
    try:
        return db.create_user(username, body.displayName.strip() or username, auth.hash_password(body.password),
                              body.isAdmin)
    except sqlite3.IntegrityError:
        raise HTTPException(400, f"“{username}” is already taken")


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserPatch, me: dict = Depends(auth.current_user)):
    if not db.get_user(user_id):
        raise HTTPException(404, "No such user")
    if user_id == me["id"] and (body.isAdmin is False or body.active is False):
        raise HTTPException(400, "You can't remove your own admin access or deactivate yourself")
    pw = None
    if body.password is not None:
        auth.validate_password(body.password)
        pw = auth.hash_password(body.password)
    user = db.update_user(user_id, display_name=(body.displayName or "").strip() or None, password_hash=pw,
                          is_admin=body.isAdmin, active=body.active)
    if (pw or body.active is False) and user_id != me["id"]:
        db.delete_user_sessions(user_id)  # signs them out everywhere
    return user


# ---------------- weeks ----------------

@router.get("/weeks/{n}")
def week_overview(n: int):
    """Every player's status for the week: saved?, points used, adjustment, unlocked."""
    w = db.get_week(n)
    info = deadline_info(n, w)
    lines = w["games"] if w else []
    picks = db.week_picks(n)
    players = []
    for u in db.list_users():
        p = picks.get(u["id"])
        row = {"user": u, "saved": has_picks(p), "adjustment": p["adjustment"] if p else 0,
               "adjNote": p["adjNote"] if p else "", "unlocked": bool(p and p["unlocked"]),
               "updatedAt": p["updatedAt"] if p else None, "total": None, "picked": 0, "score": None}
        if lines and has_picks(p):
            games = merge(lines, p, info, only_saved=True)
            chosen = [g for g in games if g["status"] != "skip"]
            s = scored(n, games, p["adjustment"])
            row.update(total=sum(int(g["points"]) for g in chosen), picked=len(chosen),
                       score=s["score"] if s["wins"] + s["losses"] + s["pushes"] else None)
        if u["active"] or p:
            players.append(row)
    return {"week": n, "games": len(lines), "hasImage": bool(w and w["hasImage"]),
            "deadlines": info["groups"], "players": players}


@router.put("/weeks/{n}/deadlines")
def set_deadlines(n: int, body: Overrides):
    w = db.get_week(n)
    current = dict((w or {}).get("deadlines") or {})
    for k, v in body.overrides.items():
        if v:
            current[k] = v
        else:
            current.pop(k, None)
    db.set_deadline_overrides(n, current)
    return deadline_info(n)["groups"]


@router.patch("/picks/{user_id}/{n}")
def set_pick(user_id: int, n: int, body: PickPatch):
    if not db.get_user(user_id):
        raise HTTPException(404, "No such user")
    db.set_pick_admin(user_id, n, body.adjustment, body.adjNote.strip(), body.unlocked)
    return {"ok": True}


@router.delete("/weeks/{n}/lines")
def delete_lines(n: int):
    db.delete_week(n)
    return {"ok": True}


# ---------------- site ----------------

@router.put("/announcement")
def set_announcement(body: Announcement):
    db.set_setting("announcement", body.text.strip())
    return {"text": body.text.strip()}


@router.get("/signup")
def get_signup():
    return auth.signup_settings()


@router.put("/signup")
def set_signup(body: Signup):
    db.set_setting("signup_open", "1" if body.open else "0")
    db.set_setting("signup_code", body.code.strip())
    return auth.signup_settings()


@router.get("/backup")
def backup(tasks: BackgroundTasks):
    tmp = Path(tempfile.mkstemp(suffix=".db")[1])
    db.backup_to(tmp)
    tasks.add_task(tmp.unlink, missing_ok=True)
    return FileResponse(tmp, media_type="application/octet-stream",
                        filename=f"pool-backup-{date.today().isoformat()}.db")


@router.post("/restore")
async def restore(request: Request):
    data = await request.body()
    if not data.startswith(b"SQLite format 3\x00"):
        raise HTTPException(400, "That file isn't a pool backup (.db)")
    tmp = db.DATA / "restore-upload.db"
    tmp.write_bytes(data)
    try:
        db.restore_from(tmp)
    except (ValueError, sqlite3.DatabaseError) as exc:
        tmp.unlink(missing_ok=True)
        raise HTTPException(400, str(exc))
    auth.bootstrap_admin()
    return {"ok": True}
