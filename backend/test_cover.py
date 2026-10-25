import unittest

from backend.cover import odds
from backend.scoring import _seconds_left, _to_endzone, score_week


class Cover(unittest.TestCase):
    def test_both_sides_add_up(self):
        # KC laying 3.5, up 4 with the ball at the LV 40, 5:00 left
        fav = odds(4, 3.5, 300, has_ball=True, yardline=40, expected=3.5)
        dog = odds(-4, -3.5, 300, has_ball=False, yardline=40, expected=-3.5)
        self.assertAlmostEqual(fav["cover"] + dog["cover"] + fav["push"], 1, places=6)
        self.assertAlmostEqual(fav["push"], dog["push"], places=6)

    def test_market_line_is_a_coin_flip_at_kickoff(self):
        for line in (3.5, -3.5, 2.5, 10.5):
            self.assertAlmostEqual(odds(0, line, 3600, expected=line)["cover"], 0.5, places=3)
        o = odds(0, 3, 3600, expected=3)
        self.assertAlmostEqual(o["cover"], o["miss"], places=3)
        self.assertGreater(o["push"], 0.05)  # games lined at 3 land on 3 a lot

    def test_better_market_line_helps(self):
        # sheet -2.5; the market moved to -3, through the key number: worth more than half a point usually is
        through_3 = odds(0, 2.5, 3600, expected=3)["cover"] - 0.5
        ordinary = odds(0, 4.5, 3600, expected=5)["cover"] - 0.5
        self.assertGreater(through_3, 0.03)
        self.assertGreater(through_3, ordinary)

    def test_game_over_in_all_but_name(self):
        self.assertGreater(odds(4, 3.5, 6, has_ball=True, yardline=70, expected=3.5)["cover"], 0.95)
        # the other team needs a touchdown from 70 yards out with 6 seconds left
        self.assertGreater(odds(4, 3.5, 6, has_ball=False, yardline=70, expected=3.5)["cover"], 0.9)

    def test_whole_number_spread_can_push(self):
        # up 3, laying 3, 2:00 left, the other team has the ball: a field goal or a stop both end at 3
        o = odds(3, 3, 120, has_ball=False, yardline=75, expected=3)
        self.assertGreater(o["push"], 0.3)
        self.assertEqual(odds(3, 3.5, 120, has_ball=False, yardline=75, expected=3)["push"], 0)

    def test_nobody_has_the_ball(self):
        o = odds(7, 3.5, 1800, expected=3.5)  # halftime
        self.assertTrue(0.5 < o["cover"] < 0.9, o)

    def test_overtime(self):
        # laying 3, tied in OT: a field goal win pushes, a touchdown (by 6 or more) covers
        o = odds(0, 3, 600, ot=True, has_ball=True, yardline=75, expected=3)
        self.assertGreater(o["push"], 0.1)
        self.assertLess(o["cover"], 0.5)


class Clock(unittest.TestCase):
    def test_seconds_left(self):
        self.assertEqual(_seconds_left(None), (3600, False))
        self.assertEqual(_seconds_left({"period": 1, "clock": "15:00"}), (3600, False))
        self.assertEqual(_seconds_left({"period": 2, "clock": "0:00"}), (1800, False))  # halftime
        self.assertEqual(_seconds_left({"period": 4, "clock": "2:05"}), (125, False))
        self.assertEqual(_seconds_left({"period": 4, "clock": "45.3"}), (45.3, False))
        self.assertEqual(_seconds_left({"period": 5, "clock": "8:00"}), (480, True))

    def test_to_endzone(self):
        self.assertEqual(_to_endzone({"possession": "DET", "spot": "DET 27"}), 73)
        self.assertEqual(_to_endzone({"possession": "LV", "spot": "LAR 48"}), 48)
        self.assertEqual(_to_endzone({"possession": "LV", "spot": "50"}), 50)
        self.assertIsNone(_to_endzone({"possession": None, "spot": None}))


def game(eid, pick, spread=3.5):
    return dict(fav="kc", dog="lv", eventId=eid, favAbbr="KC", dogAbbr="LV", spread=spread, pick=pick, points=10)


class Scoring(unittest.TestCase):
    RES = {
        "1": {"state": "in", "home_abbr": "KC", "away_abbr": "LV", "home_score": 24, "away_score": 10,
              "line": {"favorite": "KC", "spread": 3.5},
              "live": {"period": 4, "clock": "1:00", "possession": "KC", "spot": "KC 40"}},
        "2": {"state": "pre", "home_abbr": "KC", "away_abbr": "LV", "home_score": None, "away_score": None,
              "line": {"favorite": "KC", "spread": 6.5}, "live": None},
        "3": {"state": "in", "home_abbr": "KC", "away_abbr": "LV", "home_score": 7, "away_score": 0,
              "line": None, "live": None},  # live, but no clock saved
        "4": {"state": "post", "home_abbr": "KC", "away_abbr": "LV", "home_score": 20, "away_score": 10},
    }

    def test_odds_from_the_picks_side(self):
        s = score_week({"week": 1, "games": [game("1", "fav"), game("1", "dog")]}, self.RES)
        fav, dog = (g["odds"] for g in s["games"])
        self.assertGreater(fav["cover"], 0.97)  # up 14 with a minute left
        self.assertLess(dog["cover"], 0.03)

    def test_before_kickoff_uses_the_market_line(self):
        # sheet KC -3.5, market KC -6.5: KC is a good bet, LV +3.5 isn't
        s = score_week({"week": 1, "games": [game("2", "fav"), game("2", "dog")]}, self.RES)
        fav, dog = (g["odds"] for g in s["games"])
        self.assertGreater(fav["cover"], 0.55)
        self.assertLess(dog["cover"], 0.45)

    def test_no_odds_without_a_clock_or_once_final(self):
        s = score_week({"week": 1, "games": [game("3", "fav"), game("4", "fav")]}, self.RES)
        self.assertNotIn("odds", s["games"][0])
        self.assertNotIn("odds", s["games"][1])


if __name__ == "__main__":
    unittest.main()
