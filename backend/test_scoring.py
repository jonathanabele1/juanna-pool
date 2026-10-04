import unittest

from backend.scoring import score_week, season_stats, team_stats
from backend.espn import _pregame

RES = {
    "1": {"state": "post", "home_abbr": "BUF", "away_abbr": "NE", "home_score": 24, "away_score": 17},  # BUF by 7
    "2": {"state": "post", "home_abbr": "ATL", "away_abbr": "GB", "home_score": 35, "away_score": 14},
    "3": {"state": "pre", "home_abbr": "X", "away_abbr": "Y", "home_score": None, "away_score": None},
}


def game(eid, fav_abbr, spread, pick, pts, status="email", **kw):
    return dict(fav="f", dog="d", eventId=eid, favAbbr=fav_abbr, spread=spread, pick=pick, points=pts, status=status, **kw)


class Scoring(unittest.TestCase):
    def test_cover_push_loss_pending(self):
        w = {"week": 1, "adjustment": 0, "games": [
            game("1", "BUF", 6.5, "fav", 10),   # 7 > 6.5 -> win
            game("1", "BUF", 7, "fav", 5),      # push
            game("2", "GB", 3, "fav", 20),      # GB lost -> loss
            game("2", "GB", 3, "dog", 3),       # dog covers -> win
            game("3", "X", 3, "fav", 2),        # pending
        ]}
        s = score_week(w, RES)
        self.assertEqual([g["outcome"] for g in s["games"]], ["win", "push", "loss", "win", "pending"])
        self.assertEqual((s["earned"], s["wins"], s["losses"], s["pushes"], s["pending"]), (13, 2, 1, 1, 1))
        self.assertFalse(s["complete"])

    def test_live_games(self):
        res = {**RES, "4": {"state": "in", "home_abbr": "KC", "away_abbr": "LV", "home_score": 14, "away_score": 10}}
        w = {"week": 1, "adjustment": 0, "games": [
            game("1", "BUF", 6.5, "fav", 10),   # final win
            game("4", "KC", 3, "fav", 20),      # KC up 4, covering 3
            game("4", "KC", 3, "dog", 5),       # LV +3 losing by 1 against the number
            game("4", "KC", 4, "fav", 6),       # dead even with the number
            game("3", "X", 3, "fav", 2),        # not started
        ]}
        s = score_week(w, res)
        self.assertEqual([g.get("live") for g in s["games"]], [None, "win", "loss", "push", None])
        self.assertEqual(s["games"][1]["liveMargin"], 1)
        self.assertEqual(s["live"], {"wins": 1, "losses": 1, "pushes": 1, "points": 20})
        self.assertEqual(s["ifEndedNow"], 10 + 20)
        self.assertEqual(s["maxScore"], 10 + 20 + 5 + 6 + 2)

    def test_penalties_and_adjustment(self):
        gs = [game("1", "BUF", 6.5, "fav", 25 if False else 20) for _ in range(4)]  # 4 double-digit, total 80
        gs.append(game("1", "BUF", 6.5, "fav", 30, status="sent"))  # total 110 -> over by 10
        gs.append(dict(game("1", "BUF", 6.5, "fav", 2), status="skip"))
        s = score_week({"week": 1, "adjustment": -10, "games": gs}, RES)
        self.assertEqual(s["penalties"], {"over100": 20, "fourDoubleDigits": 0, "missingGames": 20})  # 5 double digits
        self.assertEqual(s["score"], 110 - 40 - 10)

    def test_four_double_digit_penalty(self):
        gs = [game("1", "BUF", 6.5, "fav", 10) for _ in range(4)] + [game("1", "BUF", 6.5, "fav", 2)] * 5
        s = score_week({"week": 1, "adjustment": 0, "games": gs}, RES)
        self.assertEqual(s["penalties"]["fourDoubleDigits"], 20)

    def test_stats(self):
        w = {"week": 1, "adjustment": 0, "games": [game("1", "BUF", 6.5, "fav", 10), game("2", "GB", 3, "fav", 50, favHome=False)]}
        st = season_stats([(1, score_week(w, RES))])
        self.assertEqual(st["record"]["wins"], 1)
        self.assertEqual(st["loy"]["outcome"], "loss")
        self.assertEqual(st["byTier"][2]["wins"], 1)


class Teams(unittest.TestCase):
    def test_team_stats(self):
        w = {"week": 1, "games": [
            dict(game("1", "BUF", 6.5, "fav", 10), dogAbbr="NE"),   # BUF 24-17 covers 6.5; I back BUF (win)
            dict(game("2", "GB", 3, "fav", 20), dogAbbr="ATL"),     # ATL 35-14: ATL covers; I back GB (loss)
        ]}
        rows = {r["abbr"]: r for r in team_stats([w], RES, {})}
        self.assertEqual(rows["BUF"]["ats"], {"w": 1, "l": 0, "p": 0})
        self.assertEqual(rows["NE"]["ats"]["l"], 1)
        self.assertEqual((rows["BUF"]["backing"]["w"], rows["BUF"]["backing"]["net"]), (1, 10))
        self.assertEqual((rows["GB"]["backing"]["l"], rows["GB"]["backing"]["net"]), (1, -20))
        self.assertEqual((rows["ATL"]["fading"]["l"], rows["ATL"]["fading"]["net"]), (1, -20))
        self.assertEqual(rows["ATL"]["su"]["w"], 1)
        self.assertEqual(rows["BUF"]["asFav"]["w"], 1)

    def test_before_week_filter(self):
        w = {"week": 4, "games": [dict(game("1", "BUF", 6.5, "fav", 10), dogAbbr="NE")]}
        self.assertEqual(team_stats([w], RES, {}, before_week=4), [])

    def test_pregame_record(self):
        self.assertEqual(_pregame("2-0", "w"), "1-0")
        self.assertEqual(_pregame("1-1", "l"), "1-0")
        self.assertEqual(_pregame("1-1-1", "t"), "1-1")


if __name__ == "__main__":
    unittest.main()
