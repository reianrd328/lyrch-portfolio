import unittest
from app import create_app
from app.models import db, User

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # Create test user
            u = User(username="testadmin", email="test@lyrch.dev")
            u.set_password("secretpass")
            db.session.add(u)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_login_page_renders(self):
        response = self.client.get("/auth/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"COMMAND ACCESS TERMINAL", response.data)

    def test_valid_login(self):
        response = self.client.post("/auth/login", data={
            "username": "testadmin",
            "password": "secretpass"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"MY WORK", response.data)
        with self.app.app_context():
            u = User.query.filter_by(username="testadmin").first()
            self.assertIsNotNone(u.active_session_token)
            self.assertIsNotNone(u.active_session_heartbeat)

    def test_second_device_blocked_while_first_device_active(self):
        # 1. Device 1 logs in
        client1 = self.app.test_client()
        client1.post("/auth/login", data={
            "username": "testadmin",
            "password": "secretpass"
        }, follow_redirects=True)

        # 2. Device 2 tries to log in
        client2 = self.app.test_client()
        res2 = client2.post("/auth/login", data={
            "username": "testadmin",
            "password": "secretpass"
        }, follow_redirects=True)

        self.assertIn(b"SECURITY LOCK", res2.data)
        self.assertIn(b"ACTIVE SESSION DETECTED", res2.data)

    def test_second_device_force_takeover(self):
        # 1. Device 1 logs in
        client1 = self.app.test_client()
        client1.post("/auth/login", data={
            "username": "testadmin",
            "password": "secretpass"
        }, follow_redirects=True)

        # 2. Device 2 logs in with force_takeover
        client2 = self.app.test_client()
        res2 = client2.post("/auth/login", data={
            "username": "testadmin",
            "password": "secretpass",
            "force_takeover": "1"
        }, follow_redirects=True)

        self.assertEqual(res2.status_code, 200)
        self.assertIn(b"MY WORK", res2.data)

        # 3. Device 1 heartbeat is now revoked
        hb1 = client1.post("/auth/heartbeat")
        self.assertEqual(hb1.status_code, 401)

    def test_close_session_beacon(self):
        # 1. Device 1 logs in
        client1 = self.app.test_client()
        client1.post("/auth/login", data={
            "username": "testadmin",
            "password": "secretpass"
        }, follow_redirects=True)

        # 2. Device 1 sends close session beacon
        res = client1.post("/auth/close-session")
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            u = User.query.filter_by(username="testadmin").first()
            self.assertIsNone(u.active_session_token)

        # 3. Device 2 can immediately log in without conflict
        client2 = self.app.test_client()
        res2 = client2.post("/auth/login", data={
            "username": "testadmin",
            "password": "secretpass"
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        self.assertNotIn(b"SECURITY LOCK", res2.data)

    def test_authenticated_user_redirects_to_admin(self):
        client = self.app.test_client()
        client.post("/auth/login", data={
            "username": "testadmin",
            "password": "secretpass"
        }, follow_redirects=True)

        # When already logged in, visiting /auth/login redirects directly to admin dashboard
        res = client.get("/auth/login")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin", res.headers["Location"])

    def test_conflict_reason_clears_session_and_shows_warning(self):
        client = self.app.test_client()
        client.post("/auth/login", data={
            "username": "testadmin",
            "password": "secretpass"
        }, follow_redirects=True)

        res = client.get("/auth/login?reason=conflict")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Your session was terminated or opened on another device", res.data)

if __name__ == "__main__":
    unittest.main()

