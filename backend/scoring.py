"""Pool scoring: pick the side that covers the *sheet* spread; earn the points if it covers.

weekly score = points on covered picks - penalties + manual adjustment (late penalties, etc.)
"""
from collections import defaultdict

LOY = 50


def _penalties(picked: list[dict], skipped: int) -> dict:
    total = sum(g["points"] for g in picked)
    over = max(0, total - 100)
    return {
        "over100": -(-over // 10) * 20 if over else 0,  # ceil(over/10)*20
        "fourDoubleDigits": 20 if sum(1 for g in picked if g["points"] >= 10) == 4 else 0,
        "missingGames": 20 * skipped,
    }


def _result(g: dict, results: dict) -> dict | None:
    """Final-or-live scores for a saved game, from the favorite's point of view."""
    res = results.get(str(g.get("eventId") or ""))
    if not res or not g.get("favAbbr"):
        return None
    fav_home = res["home_abbr"] == g["favAbbr"]
    fav = res["home_score"] if fav_home else res["away_score"]
    dog = res["away_score"] if fav_home else res["home_score"]
    out = {"state": res["state"], "fav": fav, "dog": dog, "margin": None}
    if res["state"] == "post" and fav is not None and dog is not None:
        out["margin"] = fav - dog - float(g.get("spread") or 0)  # >0: favorite covers
    return out


def score_week(week: dict, results: dict) -> dict:
    picked, per_game, skipped = [], [], 0
    for g in week["games"]:
        status = g.get("status", "email")
        if status == "skip":
            skipped += 1
            per_game.append({"outcome": "skipped"})
            continue
        pts = int(g.get("points") or 0)
        entry = {"outcome": "pending", "earned": 0, "state": None, "favScore": None, "dogScore": None}
        r = _result(g, results)
        if r:
            entry.update(state=r["state"], favScore=r["fav"], dogScore=r["dog"])
            if r["margin"] is not None:
                entry["margin"] = r["margin"]
                if r["margin"] == 0:
                    entry["outcome"] = "push"
                else:
                    won = (r["margin"] > 0) == (g.get("pick") == "fav")
                    entry["outcome"] = "win" if won else "loss"
                    entry["earned"] = pts if won else 0
        picked.append({**g, "points": pts, **entry})
        per_game.append(entry)

    pen = _penalties(picked, skipped)
    earned = sum(g["earned"] for g in picked)
    count = lambda o: sum(1 for g in picked if g["outcome"] == o)
    adjustment = int(week.get("adjustment") or 0)
    return {
        "games": per_game,
        "earned": earned,
        "wagered": sum(g["points"] for g in picked),
        "wins": count("win"), "losses": count("loss"), "pushes": count("push"),
        "pending": count("pending"),
        "penalties": pen,
        "penaltyTotal": sum(pen.values()),
        "adjustment": adjustment,
        "score": earned - sum(pen.values()) + adjustment,
        "complete": bool(picked) and count("pending") == 0,
        "_picked": picked,
    }


def season_stats(scored_weeks: list[tuple[int, dict]]) -> dict:
    weeks = [(n, s) for n, s in scored_weeks if s["wins"] + s["losses"] + s["pushes"] > 0]
    picks = [dict(g, week=n) for n, s in weeks for g in s["_picked"] if g["outcome"] in ("win", "loss", "push")]
    decided = [p for p in picks if p["outcome"] in ("win", "loss")]
    wins = [p for p in decided if p["outcome"] == "win"]

    def rate(items):
        d = [p for p in items if p["outcome"] in ("win", "loss")]
        return {"picks": len(d), "wins": sum(1 for p in d if p["outcome"] == "win"),
                "pct": round(100 * sum(1 for p in d if p["outcome"] == "win") / len(d), 1) if d else None}

    tiers = [("2–5", 2, 5), ("6–9", 6, 9), ("10–19", 10, 19), ("20", 20, 20), ("50 (LOY)", 50, 50)]
    by_tier = [{"tier": name, **rate([p for p in picks if lo <= p["points"] <= hi])} for name, lo, hi in tiers]
    scores = [(n, s["score"]) for n, s in weeks]
    best = max(scores, key=lambda x: x[1], default=None)
    worst = min(scores, key=lambda x: x[1], default=None)
    total = sum(s for _, s in scores)
    fav_home = lambda p: (p.get("favHome") if p.get("pick") == "fav" else not p.get("favHome"))
    loy = next((p for p in picks if p["points"] == LOY), None)
    return {
        "weeksPlayed": len(weeks),
        "total": total,
        "average": round(total / len(weeks), 1) if weeks else None,
        "best": {"week": best[0], "score": best[1]} if best else None,
        "worst": {"week": worst[0], "score": worst[1]} if worst else None,
        "record": {"wins": len(wins), "losses": len(decided) - len(wins),
                   "pushes": len(picks) - len(decided), "pct": rate(picks)["pct"]},
        "pointsEarned": sum(s["earned"] for _, s in weeks),
        "pointsWagered": sum(s["wagered"] for _, s in weeks),
        "penalties": sum(s["penaltyTotal"] for _, s in weeks),
        "adjustments": sum(s["adjustment"] for _, s in weeks),
        "byWeek": [{"week": n, "score": s["score"], "earned": s["earned"], "wins": s["wins"],
                    "losses": s["losses"], "pushes": s["pushes"], "complete": s["complete"]} for n, s in weeks],
        "byTier": by_tier,
        "favorites": rate([p for p in picks if p.get("pick") == "fav"]),
        "underdogs": rate([p for p in picks if p.get("pick") == "dog"]),
        "homePicks": rate([p for p in picks if fav_home(p)]),
        "awayPicks": rate([p for p in picks if not fav_home(p)]),
        "loy": ({"week": loy["week"], "pick": loy["fav"] if loy["pick"] == "fav" else loy["dog"],
                 "outcome": loy["outcome"]} if loy else None),
        "bestHit": max(wins, key=lambda p: p["points"], default=None) and _brief(max(wins, key=lambda p: p["points"])),
        "worstMiss": _brief(max((p for p in decided if p["outcome"] == "loss"), key=lambda p: p["points"], default=None)),
    }


def _brief(p):
    if not p:
        return None
    return {"week": p["week"], "team": p["fav"] if p["pick"] == "fav" else p["dog"], "points": p["points"]}


def _tally(d: dict, outcome: str) -> None:
    d[{"win": "w", "loss": "l", "push": "p"}[outcome]] += 1


def team_stats(weeks: list[dict], results: dict, teams: dict, before_week: int | None = None) -> list[dict]:
    """Per-team cover record (every game on your saved sheets) + how your own picks have fared for/against each team."""
    def blank():
        return {"games": 0, "ats": {"w": 0, "l": 0, "p": 0}, "su": {"w": 0, "l": 0, "t": 0},
                "asFav": {"w": 0, "l": 0, "p": 0}, "asDog": {"w": 0, "l": 0, "p": 0},
                "backing": {"n": 0, "w": 0, "l": 0, "p": 0, "net": 0, "pts": 0},
                "fading": {"n": 0, "w": 0, "l": 0, "p": 0, "net": 0}}

    out: dict[str, dict] = {}
    for wk in sorted(weeks, key=lambda w: w["week"]):
        if before_week is not None and wk["week"] >= before_week:
            continue
        for g in wk["games"]:
            r = _result(g, results)
            if not r or r["margin"] is None or not g.get("dogAbbr"):
                continue
            fav_a, dog_a = g["favAbbr"], g["dogAbbr"]
            fav_out = "push" if r["margin"] == 0 else "win" if r["margin"] > 0 else "loss"
            dog_out = {"win": "loss", "loss": "win", "push": "push"}[fav_out]
            for abbr, opp, outcome, role, mine, theirs in (
                (fav_a, dog_a, fav_out, "asFav", r["fav"], r["dog"]),
                (dog_a, fav_a, dog_out, "asDog", r["dog"], r["fav"]),
            ):
                t = out.setdefault(abbr, blank())
                t["games"] += 1
                _tally(t["ats"], outcome)
                _tally(t[role], outcome)
                t["su"]["w" if mine > theirs else "l" if mine < theirs else "t"] += 1
            if g.get("status") == "skip":
                continue
            pts = int(g.get("points") or 0)
            picked, other = (fav_a, dog_a) if g.get("pick") == "fav" else (dog_a, fav_a)
            mine_out = fav_out if g.get("pick") == "fav" else dog_out
            delta = pts if mine_out == "win" else -pts if mine_out == "loss" else 0
            b, f = out[picked]["backing"], out[other]["fading"]
            b["n"] += 1; b["net"] += delta; b["pts"] += pts; _tally(b, mine_out)
            f["n"] += 1; f["net"] += delta; _tally(f, mine_out)

    rows = []
    for abbr, t in out.items():
        info = teams.get(abbr, {})
        b = t["backing"]
        rows.append({
            "abbr": abbr,
            "name": f"{info.get('location', '')} {info.get('name', abbr)}".strip(),
            "short": info.get("name") or abbr,
            "logo": info.get("logo"),
            "color": info.get("color"),
            **t,
            "backing": {**b, "avgPts": round(b["pts"] / b["n"], 1) if b["n"] else None},
        })
    return sorted(rows, key=lambda r: r["name"])
