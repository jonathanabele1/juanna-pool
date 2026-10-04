"""Username/password login. Passwords are scrypt-hashed; a login sets an httpOnly session cookie.

Players create their own accounts (an admin can close sign-ups or require a join code). The very first
admin comes from the ADMIN_USERNAME / ADMIN_PASSWORD environment variables, or `python -m backend.manage`.
"""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from . import db

COOKIE = "pool_session"
SESSION_DAYS = 180
MIN_PASSWORD = 6

router = APIRouter(prefix="/api/auth")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
    except ValueError:
        return False
    return hmac.compare_digest(got.hex(), digest)


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD} characters")


def validate_username(username: str) -> str:
    name = " ".join(username.split())
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._'-]{1,29}", name):
        raise HTTPException(400, "Username must be 2–30 letters, numbers or spaces")
    return name


def bootstrap_admin() -> None:
    username, password = os.environ.get("ADMIN_USERNAME"), os.environ.get("ADMIN_PASSWORD")
    if username and password and db.count_users() == 0:
        db.create_user(username, username, hash_password(password), is_admin=True)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    user = db.session_user(_token_hash(token)) if token else None
    if not user:
        raise HTTPException(401, "Please log in")
    return user


def admin_user(user: dict = Depends(current_user)) -> dict:
    if not user["isAdmin"]:
        raise HTTPException(403, "Admins only")
    return user


# ---- crude brute-force guard: 10 failures per username or IP per 15 minutes ----
_fails: dict[str, deque] = defaultdict(deque)
WINDOW, MAX_FAILS = 15 * 60, 10


def _blocked(*keys: str) -> bool:
    now = time.time()
    for k in keys:
        q = _fails[k]
        while q and now - q[0] > WINDOW:
            q.popleft()
        if len(q) >= MAX_FAILS:
            return True
    return False


class LoginIn(BaseModel):
    username: str
    password: str


class SignupIn(BaseModel):
    username: str
    password: str
    code: str = ""


class PasswordIn(BaseModel):
    current: str
    new: str


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    username = body.username.strip()
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()
    keys = (f"u:{username.lower()}", f"ip:{ip}")
    if _blocked(*keys):
        raise HTTPException(429, "Too many attempts. Try again in a few minutes.")
    found = db.get_login(username)
    if not found or not found[0]["active"] or not check_password(body.password, found[1]):
        for k in keys:
            _fails[k].append(time.time())
        raise HTTPException(401, "Wrong username or password")
    return _start_session(found[0], request, response)


def _start_session(user: dict, request: Request, response: Response) -> dict:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    db.create_session(_token_hash(token), user["id"], expires.strftime("%Y-%m-%d %H:%M:%S"))
    https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax", secure=https)
    return user


def signup_settings() -> dict:
    return {"open": db.get_setting("signup_open", "1") == "1", "code": db.get_setting("signup_code")}


@router.get("/signup")
def signup_info():
    s = signup_settings()
    return {"open": s["open"], "needsCode": bool(s["code"])}


@router.post("/signup")
def signup(body: SignupIn, request: Request, response: Response):
    s = signup_settings()
    if not s["open"]:
        raise HTTPException(403, "Sign-ups are closed. Ask the pool admin for an account.")
    if s["code"] and not hmac.compare_digest(body.code.strip().lower(), s["code"].lower()):
        raise HTTPException(403, "That join code isn't right. Ask the pool admin for it.")
    username = validate_username(body.username)
    validate_password(body.password)
    try:
        user = db.create_user(username, username, hash_password(body.password))
    except sqlite3.IntegrityError:
        raise HTTPException(400, f"“{username}” is already taken")
    return _start_session(user, request, response)


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        db.delete_session(_token_hash(token))
    response.delete_cookie(COOKIE)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user


@router.post("/password")
def change_password(body: PasswordIn, request: Request, user: dict = Depends(current_user)):
    if not check_password(body.current, db.get_password_hash(user["id"]) or ""):
        raise HTTPException(400, "Current password is wrong")
    validate_password(body.new)
    db.update_user(user["id"], password_hash=hash_password(body.new))
    db.delete_user_sessions(user["id"], keep=_token_hash(request.cookies.get(COOKIE, "")))  # sign out other devices
    return {"ok": True}
