"""SQLite persistence. One file: $POOL_DATA_DIR/pool.db (default backend/data/pool.db).

weeks  = the week's lines (one copy, admin-owned) + the sheet image + deadline overrides
picks  = each user's pick/points/status per game, keyed by game (see game_key)
"""
import json
import os
import re
import shutil
import sqlite3
from pathlib import Path

DATA = Path(os.environ.get("POOL_DATA_DIR") or Path(__file__).parent / "data")
DATA.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA / "pool.db"

USER_FIELDS = ("status", "pick", "points")
# computed per request, never stored with the lines
VOLATILE_FIELDS = (*USER_FIELDS, "deadline", "pastDue", "locked", "kept")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE COLLATE NOCASE,
  display_name TEXT NOT NULL DEFAULT '',
  password_hash TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
-- a user is an admin when they have a row here
CREATE TABLE IF NOT EXISTS admins (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  added_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS weeks (
  week INTEGER PRIMARY KEY,
  games TEXT NOT NULL DEFAULT '[]',
  image BLOB,
  image_type TEXT,
  deadlines TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS picks (
  user_id INTEGER NOT NULL,
  week INTEGER NOT NULL,
  picks TEXT NOT NULL DEFAULT '{}',
  label TEXT NOT NULL DEFAULT '',
  adjustment INTEGER NOT NULL DEFAULT 0,
  adj_note TEXT NOT NULL DEFAULT '',
  unlocked INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, week)
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS teams (
  abbr TEXT PRIMARY KEY,
  location TEXT, name TEXT, logo TEXT, color TEXT
);
CREATE TABLE IF NOT EXISTS results (
  event_id TEXT PRIMARY KEY,
  week INTEGER,
  state TEXT,
  home_abbr TEXT, away_abbr TEXT,
  home_score INTEGER, away_score INTEGER,
  kickoff TEXT
);
"""


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _norm(s) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower())


def game_key(g: dict) -> str:
    """Stable id for a game on the sheet: the ESPN event when matched, else the sheet's team names."""
    return f"ev:{g['eventId']}" if g.get("eventId") else f"nm:{_norm(g.get('fav'))}|{_norm(g.get('dog'))}"


def _columns(c, table: str) -> set[str]:
    return {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}


def _migrate_single_user(c) -> None:
    """Pre-login databases kept lines and picks together in weeks.games. Split them; the picks go to user 1
    (the first admin, created by bootstrap_admin), and the sheet images move from files into the DB."""
    shutil.copy2(DB_PATH, DATA / "pool.pre-accounts.db")
    c.execute("ALTER TABLE weeks RENAME TO weeks_legacy")
    c.executescript(SCHEMA)
    for r in c.execute("SELECT * FROM weeks_legacy").fetchall():
        games = json.loads(r["games"])
        lines = [{k: v for k, v in g.items() if k not in VOLATILE_FIELDS} for g in games]
        picks = {game_key(g): {k: g[k] for k in USER_FIELDS if k in g} for g in games}
        img = next((DATA / "images").glob(f"week-{r['week']}.*"), None) if r["image_type"] else None
        c.execute("INSERT INTO weeks (week, games, image, image_type, updated_at) VALUES (?,?,?,?,?)",
                  (r["week"], json.dumps(lines), img.read_bytes() if img else None,
                   r["image_type"] if img else None, r["updated_at"]))
        if games:
            c.execute("INSERT INTO picks (user_id, week, picks, label, adjustment, adj_note, updated_at) "
                      "VALUES (1,?,?,?,?,?,?)",
                      (r["week"], json.dumps(picks), r["label"], r["adjustment"], r["adj_note"], r["updated_at"]))
    c.execute("DROP TABLE weeks_legacy")


def init() -> None:
    with conn() as c:
        if "adj_note" in _columns(c, "weeks"):
            _migrate_single_user(c)
        c.executescript(SCHEMA)
        if "is_admin" in _columns(c, "users"):  # admin flag moved to its own table
            c.execute("INSERT OR IGNORE INTO admins (user_id) SELECT id FROM users WHERE is_admin=1")
            c.execute("ALTER TABLE users DROP COLUMN is_admin")
        if "kickoff" not in _columns(c, "results"):
            c.execute("ALTER TABLE results ADD COLUMN kickoff TEXT")


init()


# ---------------- users + sessions ----------------

USER_SQL = "SELECT u.*, EXISTS (SELECT 1 FROM admins a WHERE a.user_id = u.id) AS is_admin FROM users u"


def _user_row(r) -> dict | None:
    if not r:
        return None
    return {"id": r["id"], "username": r["username"], "displayName": r["display_name"] or r["username"],
            "isAdmin": bool(r["is_admin"]), "active": bool(r["active"]), "createdAt": r["created_at"]}


def count_users() -> int:
    with conn() as c:
        return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def create_user(username: str, display_name: str, password_hash: str, is_admin: bool = False) -> dict:
    with conn() as c:
        cur = c.execute("INSERT INTO users (username, display_name, password_hash) VALUES (?,?,?)",
                        (username, display_name, password_hash))
        if is_admin:
            c.execute("INSERT INTO admins (user_id) VALUES (?)", (cur.lastrowid,))
        return _user_row(c.execute(f"{USER_SQL} WHERE u.id=?", (cur.lastrowid,)).fetchone())


def get_user(user_id: int) -> dict | None:
    with conn() as c:
        return _user_row(c.execute(f"{USER_SQL} WHERE u.id=?", (user_id,)).fetchone())


def get_login(username: str) -> tuple[dict, str] | None:
    """(user, password_hash) for a login attempt."""
    with conn() as c:
        r = c.execute(f"{USER_SQL} WHERE u.username=?", (username,)).fetchone()
    return (_user_row(r), r["password_hash"]) if r else None


def get_password_hash(user_id: int) -> str | None:
    with conn() as c:
        r = c.execute("SELECT password_hash FROM users WHERE id=?", (user_id,)).fetchone()
    return r["password_hash"] if r else None


def list_users() -> list[dict]:
    with conn() as c:
        return [_user_row(r) for r in c.execute(f"{USER_SQL} ORDER BY u.display_name COLLATE NOCASE, u.username")]


def update_user(user_id: int, is_admin: bool | None = None, **fields) -> dict | None:
    cols = ("display_name", "password_hash", "active")
    sets = [(k, int(v) if isinstance(v, bool) else v) for k, v in fields.items() if k in cols and v is not None]
    with conn() as c:
        if sets:
            c.execute(f"UPDATE users SET {', '.join(f'{k}=?' for k, _ in sets)} WHERE id=?",
                      [v for _, v in sets] + [user_id])
        if is_admin is True:
            c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        elif is_admin is False:
            c.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        return _user_row(c.execute(f"{USER_SQL} WHERE u.id=?", (user_id,)).fetchone())


def create_session(token_hash: str, user_id: int, expires_at: str) -> None:
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")
        c.execute("INSERT INTO sessions VALUES (?,?,?)", (token_hash, user_id, expires_at))


def session_user(token_hash: str) -> dict | None:
    with conn() as c:
        r = c.execute(f"""{USER_SQL} JOIN sessions s ON s.user_id = u.id
                          WHERE s.token_hash=? AND s.expires_at > datetime('now') AND u.active=1""",
                      (token_hash,)).fetchone()
    return _user_row(r)


def delete_session(token_hash: str) -> None:
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))


def delete_user_sessions(user_id: int, keep: str | None = None) -> None:
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE user_id=? AND token_hash IS NOT ?", (user_id, keep))


# ---------------- weeks (lines) ----------------

def _week_row(r) -> dict:
    return {
        "week": r["week"],
        "games": json.loads(r["games"]),
        "hasImage": bool(r["image_type"]),
        "deadlines": json.loads(r["deadlines"] or "{}"),
        "updatedAt": r["updated_at"],
    }


def get_week(n: int) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT week, games, image_type, deadlines, updated_at FROM weeks WHERE week=?", (n,)).fetchone()
    return _week_row(r) if r else None


def list_weeks() -> list[dict]:
    with conn() as c:
        return [_week_row(r) for r in c.execute(
            "SELECT week, games, image_type, deadlines, updated_at FROM weeks ORDER BY week")]


def _remap(old: list[dict], new: list[dict]) -> dict[str, str]:
    """Old game key -> new key, so picks survive the admin fixing names or matching a game to ESPN."""
    out = {}
    for n in new:
        nk = game_key(n)
        for o in old:
            same_event = o.get("eventId") and o.get("eventId") == n.get("eventId")
            same_names = _norm(o.get("fav")) == _norm(n.get("fav")) and _norm(o.get("dog")) == _norm(n.get("dog"))
            if (same_event or same_names) and game_key(o) != nk:
                out[game_key(o)] = nk
    return out


def save_lines(n: int, games: list[dict]) -> None:
    lines = [{k: v for k, v in g.items() if k not in VOLATILE_FIELDS} for g in games]
    with conn() as c:
        r = c.execute("SELECT games FROM weeks WHERE week=?", (n,)).fetchone()
        moves = _remap(json.loads(r["games"]), lines) if r else {}
        c.execute("""INSERT INTO weeks (week, games, updated_at) VALUES (?,?, datetime('now'))
                     ON CONFLICT(week) DO UPDATE SET games=excluded.games, updated_at=datetime('now')""",
                  (n, json.dumps(lines)))
        if moves:
            for p in c.execute("SELECT user_id, picks FROM picks WHERE week=?", (n,)).fetchall():
                picks = json.loads(p["picks"])
                for old, new in moves.items():
                    if old in picks and new not in picks:
                        picks[new] = picks.pop(old)
                c.execute("UPDATE picks SET picks=? WHERE user_id=? AND week=?", (json.dumps(picks), p["user_id"], n))


def set_image(n: int, data: bytes, content_type: str) -> None:
    with conn() as c:
        c.execute("INSERT INTO weeks (week) VALUES (?) ON CONFLICT(week) DO NOTHING", (n,))
        c.execute("UPDATE weeks SET image=?, image_type=? WHERE week=?", (data, content_type, n))


def get_image(n: int) -> tuple[bytes, str] | None:
    with conn() as c:
        r = c.execute("SELECT image, image_type FROM weeks WHERE week=?", (n,)).fetchone()
    return (r["image"], r["image_type"]) if r and r["image"] else None


def set_deadline_overrides(n: int, overrides: dict) -> None:
    with conn() as c:
        c.execute("INSERT INTO weeks (week) VALUES (?) ON CONFLICT(week) DO NOTHING", (n,))
        c.execute("UPDATE weeks SET deadlines=? WHERE week=?", (json.dumps(overrides), n))


def delete_week(n: int) -> None:
    """Removes the lines and sheet for everyone (picks stay, in case the sheet is re-uploaded)."""
    with conn() as c:
        c.execute("UPDATE weeks SET games='[]', image=NULL, image_type=NULL WHERE week=?", (n,))


# ---------------- picks ----------------

def _picks_row(r) -> dict:
    return {
        "userId": r["user_id"],
        "week": r["week"],
        "picks": json.loads(r["picks"]),
        "label": r["label"],
        "adjustment": r["adjustment"],
        "adjNote": r["adj_note"],
        "unlocked": bool(r["unlocked"]),
        "updatedAt": r["updated_at"],
    }


def get_picks(user_id: int, n: int) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM picks WHERE user_id=? AND week=?", (user_id, n)).fetchone()
    return _picks_row(r) if r else None


def user_picks(user_id: int) -> dict[int, dict]:
    with conn() as c:
        return {r["week"]: _picks_row(r) for r in c.execute("SELECT * FROM picks WHERE user_id=?", (user_id,))}


def week_picks(n: int) -> dict[int, dict]:
    with conn() as c:
        return {r["user_id"]: _picks_row(r) for r in c.execute("SELECT * FROM picks WHERE week=?", (n,))}


def save_picks(user_id: int, n: int, picks: dict, label: str, adjustment: int | None = None,
               adj_note: str | None = None) -> None:
    with conn() as c:
        c.execute("""INSERT INTO picks (user_id, week, picks, label, updated_at) VALUES (?,?,?,?, datetime('now'))
                     ON CONFLICT(user_id, week) DO UPDATE SET picks=excluded.picks, label=excluded.label,
                       updated_at=datetime('now')""",
                  (user_id, n, json.dumps(picks), label))
        if adjustment is not None:
            c.execute("UPDATE picks SET adjustment=?, adj_note=? WHERE user_id=? AND week=?",
                      (adjustment, adj_note or "", user_id, n))


def set_pick_admin(user_id: int, n: int, adjustment: int, adj_note: str) -> None:
    with conn() as c:
        c.execute("INSERT INTO picks (user_id, week) VALUES (?,?) ON CONFLICT DO NOTHING", (user_id, n))
        c.execute("UPDATE picks SET adjustment=?, adj_note=? WHERE user_id=? AND week=?",
                  (adjustment, adj_note, user_id, n))


def delete_picks(user_id: int, n: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM picks WHERE user_id=? AND week=?", (user_id, n))


# ---------------- settings ----------------

def get_setting(key: str, default: str = "") -> str:
    with conn() as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(key: str, value: str) -> None:
    with conn() as c:
        c.execute("INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


# ---------------- ESPN cache ----------------

def save_results(week: int, events: list[dict]) -> None:
    rows = [
        (e["id"], week, e["state"], e["home"]["abbr"], e["away"]["abbr"],
         e["scores"]["home"], e["scores"]["away"], e.get("kickoff"))
        for e in events
    ]
    teams = {t["abbr"]: (t["abbr"], t["location"], t["name"], t["logo"], t["color"])
             for e in events for t in (e["home"], e["away"]) if t["abbr"]}
    with conn() as c:
        c.executemany("""INSERT OR REPLACE INTO results
                         (event_id, week, state, home_abbr, away_abbr, home_score, away_score, kickoff)
                         VALUES (?,?,?,?,?,?,?,?)""", rows)
        # drop the week label from games an older bug filed under this week (results stay, keyed by event)
        ids = [e["id"] for e in events]
        c.execute(f"UPDATE results SET week=NULL WHERE week=? AND event_id NOT IN ({','.join('?' * len(ids))})",
                  [week, *ids])
        c.executemany("INSERT OR REPLACE INTO teams VALUES (?,?,?,?,?)", teams.values())


def get_results() -> dict[str, dict]:
    with conn() as c:
        return {r["event_id"]: dict(r) for r in c.execute("SELECT * FROM results")}


def kickoffs(week: int) -> dict[str, str]:
    with conn() as c:
        return {r["event_id"]: r["kickoff"] for r in c.execute(
            "SELECT event_id, kickoff FROM results WHERE week=? AND kickoff IS NOT NULL", (week,))}


def stored_events(week: int, since: str) -> list[dict]:
    """A week's games as last fetched from ESPN (the schedule doesn't change), in fetch_week's event shape."""
    with conn() as c:
        rows = c.execute("""SELECT r.*, h.location AS h_loc, h.name AS h_name, h.logo AS h_logo, h.color AS h_color,
                                   a.location AS a_loc, a.name AS a_name, a.logo AS a_logo, a.color AS a_color
                            FROM results r LEFT JOIN teams h ON h.abbr = r.home_abbr LEFT JOIN teams a ON a.abbr = r.away_abbr
                            WHERE r.week=? AND r.kickoff >= ? ORDER BY r.kickoff""", (week, since)).fetchall()
    team = lambda r, p: {"abbr": r[f"{'home' if p == 'h' else 'away'}_abbr"], "location": r[f"{p}_loc"] or "",
                         "name": r[f"{p}_name"] or r[f"{'home' if p == 'h' else 'away'}_abbr"], "logo": r[f"{p}_logo"],
                         "color": r[f"{p}_color"], "record": None}
    return [{"id": r["event_id"], "kickoff": r["kickoff"], "state": r["state"], "detail": "",
             "home": team(r, "h"), "away": team(r, "a"),
             "scores": {"home": r["home_score"], "away": r["away_score"]}, "line": None} for r in rows]


def get_teams() -> dict[str, dict]:
    with conn() as c:
        return {r["abbr"]: dict(r) for r in c.execute("SELECT * FROM teams")}


# ---------------- backup / restore ----------------

def backup_to(path: Path) -> None:
    with conn() as src, sqlite3.connect(path) as dst:
        src.backup(dst)


def restore_from(path: Path) -> None:
    """Replace the live database with an uploaded backup (validated first)."""
    with sqlite3.connect(path) as c:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "weeks" not in tables:
            raise ValueError("That file isn't a pool backup")
    shutil.copy2(DB_PATH, DATA / "pool.before-restore.db")
    os.replace(path, DB_PATH)
    init()
