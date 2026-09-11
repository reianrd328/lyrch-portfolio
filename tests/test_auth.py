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

if __name__ == "__main__":
    unittest.main()

