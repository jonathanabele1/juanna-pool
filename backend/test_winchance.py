import unittest

from backend import winchance

LINES = [
    {"fav": "kc", "dog": "lv", "spread": 3.5, "eventId": "1", "favAbbr": "KC", "dogAbbr": "LV"},  # on now
    {"fav": "buf", "dog": "ne", "spread": 6.5, "eventId": "2", "favAbbr": "BUF", "dogAbbr": "NE"},  # not started
    {"fav": "det", "dog": "gb", "spread": 2.5, "eventId": "3", "favAbbr": "DET", "dogAbbr": "GB"},  # final
]
RES = {
    "1": {"state": "in", "home_abbr": "KC", "away_abbr": "LV", "home_score": 10, "away_score": 7,
          "line": {"favorite": "KC", "spread": 3.5},
          "live": {"period": 3, "clock": "8:00", "possession": "KC", "spot": "LV 30"}},
    "2": {"state": "pre", "home_abbr": "BUF", "away_abbr": "NE", "home_score": None, "away_score": None,
          "line": {"favorite": "BUF", "spread": 6.5}, "live": None},
    "3": {"state": "post", "home_abbr": "DET", "away_abbr": "GB", "home_score": 27, "away_score": 20},
}


def entry(uid, score, picks, wins=1):
    games = [{"pick": s, "points": p} for s, p in picks]
    pending = sum(p for (s, p), g in zip(picks, LINES) if s and RES[g["eventId"]]["state"] != "post")
    return {"user": {"id": uid}, "games": games, "score": {"score": score, "wins": wins, "maxScore": score + pending}}


class WinChance(unittest.TestCase):
    def test_adds_up_to_one(self):
        c = winchance.chances(LINES, RES, [entry(1, 10, [("fav", 20), ("fav", 5), ("fav", 10)]),
                                           entry(2, 0, [("dog", 10), ("dog", 20), ("dog", 10)]),
                                           entry(3, 10, [("fav", 2), ("dog", 2), ("fav", 10)])])
        self.assertAlmostEqual(sum(c.values()), 1, delta=0.01)

    def test_hidden_picks_dont_move_anything(self):
        # the not-started game: same points, other side. Nobody's chances may change.
        a = [entry(1, 10, [("fav", 20), ("fav", 5), ("fav", 10)]), entry(2, 0, [("dog", 10), ("dog", 20), ("dog", 10)])]
        b = [entry(1, 10, [("fav", 20), ("dog", 5), ("fav", 10)]), entry(2, 0, [("dog", 10), ("fav", 20), ("dog", 10)])]
        self.assertEqual(winchance.chances(LINES, RES, a), winchance.chances(LINES, RES, b))

    def test_same_live_picks_same_chances(self):
        # (a game that hasn't started is a separate coin flip for each player, since their picks there are hidden)
        same = [("fav", 20), (None, 0), ("fav", 10)]
        c = winchance.chances(LINES, RES, [entry(1, 10, same), entry(2, 10, same), entry(3, 0, [("dog", 2), (None, 0), ("dog", 2)])])
        self.assertEqual(c[1], c[2])  # always tied, so they split every week they win

    def test_live_game_decides_it(self):
        # one game left that matters: KC up 3 with the ball at the LV 30, laying 3.5. Whoever has KC is the favorite.
        c = winchance.chances(LINES, RES, [entry(1, 10, [("fav", 20), (None, 0), ("fav", 10)]),
                                           entry(2, 10, [("dog", 20), (None, 0), ("fav", 10)])])
        self.assertGreater(c[1], 0.5)
        self.assertAlmostEqual(c[1] + c[2], 1, delta=0.01)

    def test_clinched_and_eliminated(self):
        c = winchance.chances(LINES, RES, [entry(1, 60, [("fav", 2), ("fav", 2), ("fav", 10)]),
                                           entry(2, 10, [("dog", 20), ("dog", 20), ("dog", 10)])])
        self.assertEqual(c, {1: 1.0, 2: 0.0})  # 2 can reach 50 at most

    def test_long_shot_is_never_shown_as_zero(self):
        # 2 needs both games and a lot of luck, but can still get there
        c = winchance.chances(LINES, RES, [entry(1, 30, [("fav", 2), ("fav", 2), ("fav", 10)]),
                                           entry(2, 0, [("dog", 20), ("dog", 20), ("dog", 10)])])
        self.assertGreater(c[2], 0)
        self.assertLess(c[1], 1)

    def test_nothing_left_to_decide(self):
        done = {**RES, "1": {**RES["1"], "state": "post"}, "2": {**RES["2"], "state": "post", "home_score": 20, "away_score": 3}}
        self.assertIsNone(winchance.chances(LINES, done, [entry(1, 10, [("fav", 2)] * 3)]))


if __name__ == "__main__":
    unittest.main()
