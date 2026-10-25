import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from backend import auth, db, espn


class Mail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.patches = [mock.patch.object(db, "DB_PATH", Path(cls.tmp.name) / "pool.db"),
                       mock.patch.object(espn, "_fetch_week", lambda week=None: {"week": 6, "fetchedAt": 0, "events": []})]
        for p in cls.patches:
            p.start()
        db.init()
        from backend.main import app
        cls.app = app
        h = auth.hash_password("secret1")
        cls.boss = db.create_user("boss", "Boss", h, is_admin=True)
        cls.ann = db.create_user("ann", "Ann", h)

    @classmethod
    def tearDownClass(cls):
        for p in cls.patches:
            p.stop()
        cls.tmp.cleanup()

    def client(self, username):
        c = TestClient(self.app)
        c.post("/api/auth/login", json={"username": username, "password": "secret1"}).raise_for_status()
        return c

    def test_league_emails_by_week(self):
        boss = self.client("boss")
        r = boss.put("/api/admin/league-emails", json={"emails": {"6": " pool6@example.com ", "7": "pool7@example.com", "8": ""}})
        self.assertEqual(r.json(), {"6": "pool6@example.com", "7": "pool7@example.com"})
        ann = self.client("ann")
        self.assertEqual(ann.get("/api/weeks/6").json()["leagueEmail"], "pool6@example.com")
        self.assertEqual(ann.get("/api/weeks/8").json()["leagueEmail"], "")

    def test_league_emails_are_admin_only_and_checked(self):
        self.assertEqual(self.client("ann").put("/api/admin/league-emails", json={"emails": {"6": "x@y.com"}}).status_code, 403)
        boss = self.client("boss")
        self.assertEqual(boss.put("/api/admin/league-emails", json={"emails": {"6": "not an email"}}).status_code, 400)
        self.assertEqual(boss.put("/api/admin/league-emails", json={"emails": {"30": "x@y.com"}}).status_code, 400)

    def test_mail_prefs_are_private(self):
        ann = self.client("ann")
        saved = {"app": "gmail", "sender": "ann@gmail.com", "teamName": "Ann's Army"}
        self.assertEqual(ann.put("/api/auth/mail", json={**saved, "teamName": "  Ann's   Army "}).json(), saved)
        self.assertEqual(ann.get("/api/auth/mail").json(), saved)
        self.assertEqual(ann.put("/api/auth/mail", json={"app": "pigeon"}).status_code, 422)
        self.assertEqual(ann.put("/api/auth/mail", json={"app": "outlook-work"}).status_code, 422)
        self.assertEqual(ann.put("/api/auth/mail", json={"app": "gmail", "sender": "nope"}).status_code, 400)
        # the address never reaches other players (or the admin's account list)
        self.assertNotIn("ann@gmail.com", self.client("boss").get("/api/admin/users").text)
        self.assertNotIn("ann@gmail.com", self.client("boss").get("/api/players").text)


if __name__ == "__main__":
    unittest.main()
