"""Builds backend/cover_table.json (see backend/cover.py) from nflverse play-by-play, and checks it on held-out seasons.

    pip install pandas pyarrow
    python scripts/build_cover_table.py PBP_DIR

PBP_DIR holds play_by_play_<year>.parquet files from
https://github.com/nflverse/nflverse-data/releases/tag/pbp (2012–2025 used for the shipped table).
"""
import json
import math
import sys
from pathlib import Path
from statistics import NormalDist

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import cover  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "backend" / "cover_table.json"
TIME_EDGES = [15, 30, 60, 90, 120, 180, 240, 300, 420, 600, 900, 1200, 1500, 1800, 2100, 2400, 2700, 3000, 3300]
OT_EDGES = [120, 300]
MARGIN_EDGES = [-16, -8, -3, 0, 1, 4, 9, 17]  # ≤-17, -16..-9, -8..-4, -3..-1, 0, 1..3, 4..8, 9..16, ≥17
FIELD_EDGES = [11, 21, 41, 61, 81]  # yards to the opponent's end zone: 1-10, 11-20, 21-40, 41-60, 61-80, 81-99
ZONE_EDGES = [21, 61]  # coarser fallback: red zone, 21-60, own side
MIN_N = 80  # games a cell needs before it's used on its own (otherwise a coarser cell is)
TEST = (2024, 2025)
COLS = ["season", "game_id", "qtr", "game_seconds_remaining", "posteam", "home_team", "yardline_100",
        "posteam_score", "defteam_score", "result", "spread_line", "vegas_wp"]


def load(pbp_dir: Path) -> pd.DataFrame:
    d = pd.concat(pd.read_parquet(f, columns=COLS) for f in sorted(pbp_dir.glob("play_by_play_*.parquet")))
    d = d.dropna(subset=["posteam", "yardline_100", "posteam_score", "defteam_score", "result", "spread_line",
                         "game_seconds_remaining"])
    home = d.posteam == d.home_team
    d = d.assign(
        ot=d.qtr >= 5,
        t=d.game_seconds_remaining.clip(0, 3600),
        margin=(d.posteam_score - d.defteam_score).astype(int),
        final=d.result.where(home, -d.result).astype(int),
        s=d.spread_line.where(home, -d.spread_line),  # market expected margin for the team with the ball
    )
    d["delta"] = d.final - d.margin
    d["tb"] = [f"o{cover._bin(OT_EDGES, t)}" if ot else f"r{cover._bin(TIME_EDGES, t)}" for t, ot in zip(d.t, d.ot)]
    d["mb"] = [cover._bin(MARGIN_EDGES, m) for m in d.margin]
    d["fb"] = [cover._bin(FIELD_EDGES, y) for y in d.yardline_100]
    d["zb"] = [f"z{cover._bin(ZONE_EDGES, y)}" for y in d.yardline_100]
    return d


def build(d: pd.DataFrame) -> dict:
    cells = {}
    # every cell cover.keys() can ask for: (margin, field) columns, None for "any"
    levels = [("mb", "fb"), ("mb", "zb"), ("mb", None), (None, "fb"), (None, None)]
    for level in levels:
        cols = ["tb", *(c for c in level if c)]
        for k, g in d.groupby(cols):
            games = g.game_id.nunique()
            if games < MIN_N and level != (None, None):
                continue
            parts = dict(zip(cols, map(str, k)))
            key = "|".join([parts["tb"], *(parts[c] if c else "*" for c in level)])
            # every game counts once per cell, however many plays it ran from that spot
            w = 1 / g.groupby("game_id").game_id.transform("size")
            w = w / w.sum()
            dist = w.groupby(g.delta).sum()
            cells[key] = {"n": games, "md": round(float((w * g.delta).sum()), 3), "ms": round(float((w * g.s).sum()), 3),
                          "d": {str(int(v)): round(float(p), 4) for v, p in dist.items() if p >= 1e-4}}
    # β: how much of the market's expected margin shows up over the rest of the game. Fitted on the data it comes out
    # ~1.1 (favorites would be ~53% to cover their own closing line at kickoff); 1 keeps a line that matches the
    # market at a coin flip, which is the honest thing to show.
    beta = 1.0
    return {"beta": round(beta, 4), "timeEdges": TIME_EDGES, "otEdges": OT_EDGES, "marginEdges": MARGIN_EDGES,
            "fieldEdges": FIELD_EDGES, "zoneEdges": ZONE_EDGES, "cells": cells}


N = NormalDist()


def _sd(t):
    return max(13.5 * math.sqrt(t / 3600), 0.5)


def normal(margin, need, t, expected):
    """The plain model: final margin ~ Normal(margin + expected·f, 13.5·√f)."""
    return _normal(margin + expected * t / 3600, need, _sd(t))


def from_wp(margin, need, t, wp):
    """Back the expected final margin out of a win probability (nflfastR's here, ESPN's live), then the plain model."""
    wp = min(max(wp, 0.002), 0.998)
    return _normal(_sd(t) * N.inv_cdf(wp), need, _sd(t))


def _normal(mu, need, sd):
    if need != int(need):
        return 1 - N.cdf((need - mu) / sd), 0.0
    hi, lo = 1 - N.cdf((need + 0.5 - mu) / sd), N.cdf((need - 0.5 - mu) / sd)
    return hi, 1 - hi - lo


def evaluate(test: pd.DataFrame, table: dict) -> None:
    cover._table.cache_clear()
    OUT.write_text(json.dumps(table))  # cover.py reads the file; the final table overwrites it below
    test = test[~test.ot & test.vegas_wp.notna()].sample(min(len(test), 30000), random_state=1)
    rows = []
    for r in test.itertuples():
        need = r.s  # the pos team covers its closing line if final > s
        o = cover.odds(r.margin, need, r.t, has_ball=True, yardline=r.yardline_100, expected=r.s)
        rows.append({"t": r.t, "y_c": float(r.final > need), "y_p": float(r.final == need),
                     "table": (o["cover"], o["push"]), "normal": normal(r.margin, need, r.t, r.s),
                     "wp": from_wp(r.margin, need, r.t, r.vegas_wp)})
    eps = 1e-4

    def score(rs, m):
        brier = sum((x[m][0] - x["y_c"]) ** 2 + (x[m][1] - x["y_p"]) ** 2 for x in rs) / len(rs)
        ll = -sum(math.log(max(eps, x[m][0] if x["y_c"] else x[m][1] if x["y_p"] else 1 - x[m][0] - x[m][1]))
                  for x in rs) / len(rs)
        return brier, ll

    spans = [("whole game", 0, 3601), ("first 5:00", 3300, 3601), ("Q1–Q3", 900, 3601), ("Q4 15:00–5:00", 300, 900),
             ("last 5:00", 60, 300), ("last 1:00", 0, 60)]
    print(f"\nHeld-out seasons {TEST}, {len(rows)} plays. Brier (lower is better) / log loss")
    print(f"{'':<16}{'plays':>7}  {'table':>15}  {'normal':>15}  {'win-prob':>15}")
    for name, lo, hi in spans:
        rs = [x for x in rows if lo <= x["t"] < hi]
        cols = "  ".join("{:.4f} / {:.3f}".format(*score(rs, m)) for m in ("table", "normal", "wp"))
        print(f"{name:<16}{len(rs):>7}  {cols}")
    print("\nCalibration of the table (predicted cover vs. actual):")
    for lo in range(0, 100, 10):
        rs = [x for x in rows if lo / 100 <= x["table"][0] < (lo + 10) / 100]
        if rs:
            print(f"  {lo:>2}–{lo + 10:<3}%  {len(rs):>6} plays  predicted {100 * sum(x['table'][0] for x in rs) / len(rs):5.1f}%"
                  f"  actual {100 * sum(x['y_c'] for x in rs) / len(rs):5.1f}%")
    rs = [x for x in rows if x["t"] < 300]
    print(f"\nPushes, last 5:00: predicted {100 * sum(x['table'][1] for x in rs) / len(rs):.1f}% (table), "
          f"{100 * sum(x['normal'][1] for x in rs) / len(rs):.1f}% (normal), actual {100 * sum(x['y_p'] for x in rs) / len(rs):.1f}%")


def main():
    d = load(Path(sys.argv[1]))
    evaluate(d[d.season.isin(TEST)], build(d[~d.season.isin(TEST)]))
    table = build(d)
    OUT.write_text(json.dumps(table, separators=(",", ":")))
    print(f"\nWrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(table['cells'])} cells, beta {table['beta']})")


if __name__ == "__main__":
    main()
