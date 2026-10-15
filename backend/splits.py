"""DraftKings public betting splits (% of bets and % of money on each side of the spread).

DraftKings publishes these on DK Network as a plain HTML page, 10 games per page. Games drop off that page once
they kick off, so each game's last-seen split is saved and keeps showing afterwards (the "closing" split).
"""
import html
import re
import time

import httpx

from . import db, espn

URL = "https://dknetwork.draftkings.com/draftkings-sportsbook-betting-splits/"
PARAMS = {"tb_eg": "88808", "tb_edate": "n7days", "tb_emt": "Spread"}  # 88808 = NFL
TTL = 10 * 60
MAX_PAGES = 4

_cache: dict = {"at": 0.0, "games": []}


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _pct(s: str) -> int | None:
    m = re.search(r"(\d+)%", s)
    return int(m.group(1)) if m else None


def parse(page: str) -> list[dict]:
    """[{away, home, sides: [{abbr, nick, line, odds, bets, handle}]}] from one splits page."""
    out = []
    for block in page.split('class="tb-se ')[1:]:
        title = re.search(r'class="tb-se-title-new[^"]*"[^>]*>(.*?)</h5>', block, re.S)
        if not title or "@" not in _text(title.group(1)):
            continue
        away, home = (x.strip() for x in _text(title.group(1)).split("@", 1))
        sides = []
        for row in re.findall(r'class="tb-sodd[^"]*"(.*?)(?=class="tb-sodd|class="tb-se-head|$)', block, re.S):
            label = re.search(r'class="tb-slipline[^"]*">(.*?)</div>', row, re.S)
            cells = re.findall(r'<div class="flex-1">\s*(\d+%)', row)
            odds = re.search(r'class="tb-odd-s[^"]*"[^>]*>(.*?)</a>', row, re.S)
            if not label or len(cells) < 2:
                continue
            m = re.match(r"(\S+)\s+(.*?)\s*([+\-−]\d+(?:\.\d+)?|PK|pk)?$", _text(label.group(1)))
            if not m:
                continue
            sides.append({"abbr": m.group(1), "nick": m.group(2), "line": (m.group(3) or "").replace("−", "-"),
                          "odds": _text(odds.group(1)).replace("−", "-") if odds else None,
                          "handle": _pct(cells[0]), "bets": _pct(cells[1])})
        if len(sides) == 2:
            out.append({"away": away, "home": home, "sides": sides})
    return out


def fetch() -> list[dict]:
    """Every upcoming NFL game on DK's splits page (cached; [] if DraftKings can't be reached)."""
    now = time.time()
    if now - _cache["at"] < TTL:
        return _cache["games"]
    games, seen = [], set()
    try:
        for page in range(1, MAX_PAGES + 1):
            r = httpx.get(URL, params={**PARAMS, "tb_page": page}, timeout=15,
                          headers={"User-Agent": "Mozilla/5.0 (pool site)"})
            r.raise_for_status()
            found = [g for g in parse(r.text) if (g["away"], g["home"]) not in seen]
            if not found:
                break
            seen.update((g["away"], g["home"]) for g in found)
            games += found
    except httpx.HTTPError:
        if not games:
            _cache["at"] = now - TTL + 60  # try again in a minute
            return _cache["games"]
    _cache.update(at=now, games=games)
    return games


def _nick(s: str) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower())


def for_week(week: int) -> dict[str, dict]:
    """ESPN event id -> {sides: {abbr: {bets, handle, line, odds}}, updatedAt}, for the week's games."""
    try:
        events = espn.fetch_week(week)["events"]
    except Exception:  # ESPN down: whatever was saved
        return db.get_splits()
    by_names = {(_nick(e["away"]["name"]), _nick(e["home"]["name"])): e for e in events if e["state"] == "pre"}
    fresh = {}
    if by_names:
        for g in fetch():
            # DK labels sides "SEA Seahawks"; match on the nickname (DK and ESPN abbreviations differ, e.g. WAS/WSH)
            ev = by_names.get((_nick(g["away"].split(" ", 1)[-1]), _nick(g["home"].split(" ", 1)[-1])))
            if not ev:
                continue
            sides = {}
            for s in g["sides"]:
                team = next((t for t in (ev["home"], ev["away"]) if _nick(t["name"]) == _nick(s["nick"])), None)
                if team:
                    sides[team["abbr"]] = {k: s[k] for k in ("bets", "handle", "line", "odds")}
            if len(sides) == 2:
                fresh[ev["id"]] = {"sides": sides}
        if fresh:
            db.save_splits(fresh)
    return db.get_splits([e["id"] for e in events])
