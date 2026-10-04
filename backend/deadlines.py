"""Pick deadlines: one hour before the first game of each day (ET).

Sunday and Monday games are picked together, due at noon ET Sunday (earlier if a Sunday game,
e.g. London, kicks off before 1 PM). The admin can override any day's deadline.
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _parse(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute(kickoffs: dict[str, str], overrides: dict[str, str] | None = None) -> dict:
    """kickoffs: ESPN event id -> ISO kickoff. Returns the week's deadline groups and each event's deadline."""
    overrides = overrides or {}
    groups: dict = {}  # ET date of the group -> {first, events, days}
    for eid, iso in kickoffs.items():
        k = _parse(iso)
        et = k.astimezone(ET)
        day = et.date()
        if et.weekday() in (0, 1):  # Monday/Tuesday games ride with that weekend's Sunday picks
            day -= timedelta(days=et.weekday() + 1)
        g = groups.setdefault(day, {"first": k, "events": [], "days": set()})
        g["first"] = min(g["first"], k)
        g["events"].append(eid)
        g["days"].add(et.weekday())

    out, by_event = [], {}
    for day in sorted(groups):
        g = groups[day]
        auto = g["first"] - timedelta(hours=1)
        if day.weekday() == 6:
            auto = min(auto, datetime.combine(day, time(12), ET).astimezone(timezone.utc))
        override = overrides.get(day.isoformat())
        deadline = _parse(override) if override else auto
        names = [DAY_NAMES[d] for d in sorted(g["days"], key=lambda d: (d - day.weekday()) % 7)]
        out.append({"id": day.isoformat(), "label": " & ".join(names), "games": len(g["events"]),
                    "deadline": _iso(deadline), "auto": _iso(auto), "overridden": bool(override)})
        for eid in g["events"]:
            by_event[eid] = _iso(deadline)

    # games we can't place (no ESPN match) fall in with the Sunday picks, else the last group
    fallback = next((o["deadline"] for o in out if datetime.fromisoformat(o["id"]).weekday() == 6),
                    out[-1]["deadline"] if out else None)
    return {"groups": out, "byEvent": by_event, "fallback": fallback}


def deadline_for(game: dict, info: dict) -> str | None:
    return info["byEvent"].get(str(game.get("eventId") or "")) or info["fallback"]


def is_past(deadline: str | None, now: datetime | None = None) -> bool:
    return bool(deadline) and _parse(deadline) <= (now or datetime.now(timezone.utc))
