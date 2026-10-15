import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from backend import auth, db, espn, splits

TEAM = lambda abbr, name: {"abbr": abbr, "location": abbr, "name": name, "logo": None, "color": None, "record": None}


def event(eid, home, away, state, hs=None, as_=None, kickoff="2026-10-11T17:00Z"):
    return {"id": eid, "kickoff": kickoff, "state": state, "detail": "", "live": None,
            "home": TEAM(*home), "away": TEAM(*away), "scores": {"home": hs, "away": as_}, "line": None}


EVENTS = [
    event("1", ("BUF", "Bills"), ("NE", "Patriots"), "post", 24, 17),  # BUF by 7
    event("2", ("ATL", "Falcons"), ("GB", "Packers"), "in", 14, 10),   # ATL up 4, live
    event("3", ("DEN", "Broncos"), ("SEA", "Seahawks"), "pre"),        # not started
]
LINES = [
    {"fav": "buf", "dog": "ne", "spread": 3, "eventId": "1", "favAbbr": "BUF", "dogAbbr": "NE", "favHome": True},
    {"fav": "atl", "dog": "gb", "spread": 2, "eventId": "2", "favAbbr": "ATL", "dogAbbr": "GB", "favHome": True},
    {"fav": "sea", "dog": "den", "spread": 2.5, "eventId": "3", "favAbbr": "SEA", "dogAbbr": "DEN", "favHome": False},
]


def fake_fetch(week=None):
    data = {"week": 6, "fetchedAt": 0, "events": EVENTS}
    db.save_results(6, EVENTS)
    return data


def picks(*sides):
    return {db.game_key(g): {"pick": s, "points": p} for g, (s, p) in zip(LINES, sides) if s}


class League(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.patches = [mock.patch.object(db, "DB_PATH", Path(cls.tmp.name) / "pool.db"),
                       mock.patch.object(espn, "_fetch_week", fake_fetch)]
        for p in cls.patches:
            p.start()
        db.init()
        from backend.main import app
        cls.app = app
        h = auth.hash_password("secret1")
        cls.me = db.create_user("me", "Me", h)
        cls.ann = db.create_user("ann", "Ann", h)
        cls.bob = db.create_user("bob", "Bob", h)
        db.create_user("cal", "Cal", h)  # no picks
        db.save_lines(6, LINES)
        db.save_picks(cls.me["id"], 6, picks(("fav", 10), ("fav", 5), ("dog", 20)), "")
        db.save_picks(cls.ann["id"], 6, picks(("dog", 30), ("fav", 8), ("fav", 2)), "")
        db.save_picks(cls.bob["id"], 6, picks(("fav", 4), (None, 0), ("fav", 50)), "")

    @classmethod
    def tearDownClass(cls):
        for p in cls.patches:
            p.stop()
        cls.tmp.cleanup()

    def client(self):
        c = TestClient(self.app)
        c.post("/api/auth/login", json={"username": "me", "password": "secret1"}).raise_for_status()
        return c

    def test_other_players_unstarted_picks_are_hidden(self):
        w = self.client().get(f"/api/players/{self.ann['id']}/weeks/6").json()
        self.assertEqual([g.get("pick") for g in w["games"]], ["dog", "fav", None])
        self.assertTrue(w["games"][2]["hidden"])
        self.assertIsNone(w["games"][2]["points"])
        self.assertEqual(w["score"]["games"][2], {"outcome": "hidden"})
        self.assertEqual(w["hiddenCount"], 1)

    def test_my_own_picks_are_never_hidden(self):
        w = self.client().get(f"/api/players/{self.me['id']}/weeks/6").json()
        self.assertEqual([g["pick"] for g in w["games"]], ["fav", "fav", "dog"])

    def test_week_standings_live_projection(self):
        s = self.client().get("/api/standings/week/6").json()
        rows = {r["name"]: r for r in s["rows"]}
        # me: BUF -3 covered (+10), ATL -2 covering live (+5 if it ends now)
        self.assertEqual((rows["Me"]["score"], rows["Me"]["projected"]), (10, 15))
        # ann: NE +3 missed, ATL covering live (+8)
        self.assertEqual((rows["Ann"]["score"], rows["Ann"]["projected"]), (0, 8))
        # bob: BUF covered (+4), skipped the live ATL game (−20)
        self.assertEqual(rows["Bob"]["score"], 4 - 20)
        self.assertEqual([r["name"] for r in s["rows"]], ["Me", "Ann", "Bob"])
        self.assertEqual(rows["Me"]["projectedRank"], 1)
        self.assertEqual(s["noPicks"], ["Cal"])
        self.assertEqual(s["games"], {"total": 3, "live": 1, "final": 1})

    def test_pool_split_only_for_started_games(self):
        p = self.client().get("/api/weeks/6/pool").json()
        g1, g2, g3 = p["games"]
        self.assertEqual((g1["fav"], g1["dog"]), ({"count": 2, "points": 14}, {"count": 1, "points": 30}))
        self.assertEqual(g2["none"], 1)
        self.assertEqual([x["name"] for x in g1["picks"]], ["Ann", "Me", "Bob"])  # most points first
        self.assertEqual(g3, {"key": "ev:3", "revealed": False})

    def test_season_standings(self):
        rows = self.client().get("/api/standings/season").json()["rows"]
        self.assertEqual([(r["name"], r["rank"], r["total"]) for r in rows], [("Me", 1, 10), ("Ann", 2, 0), ("Bob", 3, -16)])

    def test_players_list(self):
        names = [p["displayName"] for p in self.client().get("/api/players").json()]
        self.assertEqual(sorted(names), ["Ann", "Bob", "Cal", "Me"])

    def test_hidden_accounts_are_left_out_of_the_league(self):
        db.update_user(self.bob["id"], hidden=True)
        try:
            c = self.client()
            self.assertNotIn("Bob", [r["name"] for r in c.get("/api/standings/week/6").json()["rows"]])
            self.assertNotIn("Bob", [r["name"] for r in c.get("/api/standings/season").json()["rows"]])
            self.assertNotIn("Bob", [p["displayName"] for p in c.get("/api/players").json()])
            g1 = c.get("/api/weeks/6/pool").json()["games"][0]
            self.assertEqual(g1["fav"]["count"] + g1["dog"]["count"], 2)  # Bob's BUF pick isn't counted
            self.assertEqual(c.get(f"/api/players/{self.bob['id']}/weeks/6").status_code, 404)
            # ...but Bob still sees himself
            b = TestClient(self.app)
            b.post("/api/auth/login", json={"username": "bob", "password": "secret1"}).raise_for_status()
            self.assertIn("Bob", [r["name"] for r in b.get("/api/standings/week/6").json()["rows"]])
        finally:
            db.update_user(self.bob["id"], hidden=False)

    def test_admin_deletes_a_user_and_their_picks(self):
        h = auth.hash_password("secret1")
        tmp = db.create_user("temp", "Temp", h)
        db.save_picks(tmp["id"], 6, picks(("fav", 5), (None, 0), (None, 0)), "")
        c = self.client()
        self.assertEqual(c.delete(f"/api/admin/users/{tmp['id']}").status_code, 403)  # admins only
        db.update_user(self.me["id"], is_admin=True)
        try:
            self.assertEqual(c.delete(f"/api/admin/users/{self.me['id']}").status_code, 400)  # not yourself
            c.delete(f"/api/admin/users/{tmp['id']}").raise_for_status()
            self.assertIsNone(db.get_user(tmp["id"]))
            self.assertNotIn(tmp["id"], db.week_picks(6))
        finally:
            db.update_user(self.me["id"], is_admin=False)

    def test_test_live_mode_is_admin_only_and_saves_nothing(self):
        demo_header = {"X-Demo-Live": "1"}
        before = db.get_results(real=True)
        c = self.client()  # not an admin: the header does nothing
        self.assertNotIn("demo", c.get("/api/lines?week=6", headers=demo_header).json())
        db.update_user(self.me["id"], is_admin=True)
        try:
            board = c.get("/api/lines?week=6", headers=demo_header).json()
            self.assertTrue(board["demo"])
            fake = {e["id"]: e for e in board["events"]}
            self.assertEqual([fake[i]["state"] for i in "123"], ["post", "in", "pre"])  # 3 games: 1 final, 1 live
            live = c.get("/api/standings/week/6", headers=demo_header).json()["rows"]
            real = c.get("/api/standings/week/6").json()["rows"]
            # same picks scored against the fake scores instead of the real ones
            self.assertNotEqual([r["projected"] for r in live], [r["projected"] for r in real])
            w = c.get(f"/api/players/{self.ann['id']}/weeks/6", headers=demo_header).json()
            # game 2 is really live: Ann's real pick shows; game 1 is fake-final but really final too
            self.assertEqual(w["games"][1]["pick"], "fav")
            self.assertEqual(db.get_results(real=True), before)  # nothing fake was saved
            self.assertEqual(c.get("/api/standings/week/6").json()["games"]["live"], 1)  # header off: real again
        finally:
            db.update_user(self.me["id"], is_admin=False)


PAGE = """
<div class="tb-se border-b"><div class="tb-se-title flex"><h5 class="tb-se-title-new mt-0"><a href="#">
  <img src="x.png"/> SEA Seahawks @ <img src="y.png"/>DEN Broncos </a></h5></div>
  <div class="tb-se-head flex"><div class="flex-1">Spread</div></div>
  <div class="tb-sodd flex"><div class="tb-slipline flex-1 font-medium">SEA Seahawks −2.5</div>
    <div class="flex-1"><a class="tb-odd-s bg" href="#">−112</a></div>
    <div class="flex-1">80% <div class="tb-progress"></div></div><div class="flex-1">75% <div></div></div></div>
  <div class="tb-sodd flex"><div class="tb-slipline flex-1 font-medium">DEN Broncos +2.5</div>
    <div class="flex-1"><a class="tb-odd-s bg" href="#">−108</a></div>
    <div class="flex-1">20% <div class="tb-progress"></div></div><div class="flex-1">25% <div></div></div></div>
</div>
"""


class Splits(unittest.TestCase):
    def test_parse(self):
        [g] = splits.parse(PAGE)
        self.assertEqual((g["away"], g["home"]), ("SEA Seahawks", "DEN Broncos"))
        self.assertEqual(g["sides"][0], {"abbr": "SEA", "nick": "Seahawks", "line": "-2.5", "odds": "-112",
                                         "handle": 80, "bets": 75})
        self.assertEqual(g["sides"][1]["bets"], 25)


if __name__ == "__main__":
    unittest.main()
