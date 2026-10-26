import unittest

from backend.deadlines import compute, reveal_at

# week 5, 2026: Thursday night, a London game Sunday morning, Sunday afternoon, Monday night
KICKOFFS = {
    "thu": "2026-10-09T00:15Z",   # Thu 8:15 PM ET
    "lon": "2026-10-11T13:30Z",   # Sun 9:30 AM ET
    "sun": "2026-10-11T17:00Z",   # Sun 1:00 PM ET
    "mon": "2026-10-13T00:15Z",   # Mon 8:15 PM ET
}


class Deadlines(unittest.TestCase):
    def test_thursday_hour_before_and_sunday_monday_together(self):
        d = compute({k: v for k, v in KICKOFFS.items() if k != "lon"})
        self.assertEqual([(g["label"], g["deadline"]) for g in d["groups"]],
                         [("Thursday", "2026-10-08T23:15:00Z"), ("Sunday & Monday", "2026-10-11T16:00:00Z")])  # noon ET
        self.assertEqual(d["byEvent"]["mon"], "2026-10-11T16:00:00Z")

    def test_early_sunday_game_moves_sunday_deadline(self):
        d = compute(KICKOFFS)
        self.assertEqual(d["byEvent"]["sun"], "2026-10-11T12:30:00Z")  # 8:30 AM ET

    def test_override(self):
        d = compute(KICKOFFS, {"2026-10-08": "2026-10-08T23:30:00Z"})
        thu = d["groups"][0]
        self.assertTrue(thu["overridden"])
        self.assertEqual((thu["deadline"], thu["auto"]), ("2026-10-08T23:30:00Z", "2026-10-08T23:15:00Z"))

    def test_unmatched_game_uses_sunday(self):
        self.assertEqual(compute(KICKOFFS)["fallback"], "2026-10-11T12:30:00Z")


class Reveal(unittest.TestCase):
    def test_sunday_1pm_et(self):
        self.assertEqual(reveal_at(KICKOFFS.values()).isoformat(), "2026-10-11T17:00:00+00:00")

    def test_london_game_doesnt_move_it(self):
        self.assertEqual(reveal_at([KICKOFFS["thu"], KICKOFFS["lon"]]).isoformat(), "2026-10-11T17:00:00+00:00")

    def test_after_daylight_saving_ends(self):
        self.assertEqual(reveal_at(["2026-11-08T18:00Z"]).isoformat(), "2026-11-08T18:00:00+00:00")  # 1 PM EST

    def test_no_sunday_game_known(self):
        self.assertIsNone(reveal_at([KICKOFFS["thu"], None]))


if __name__ == "__main__":
    unittest.main()
