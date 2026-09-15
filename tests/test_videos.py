import unittest
from app import create_app
from app.models import db, Video, User

class VideoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            u = User(username="admin", email="admin@lyrch.dev")
            u.set_password("adminpass")
            db.session.add(u)

            v1 = Video(
                title="AI Kung Fu Scene",
                slug="ai-kung-fu-scene",
                album="Kung Fu Chronicles",
                tools_used="Gemini, Video Edit",
                duration="0:10",
                featured=True,
                visibility="published"
            )
            v2 = Video(
                title="AI Kung Fu Finale",
                slug="ai-kung-fu-finale",
                album="Kung Fu Chronicles",
                tools_used="Gemini, Video Edit",
                duration="0:15",
                featured=False,
                visibility="published"
            )
            v3 = Video(
                title="Coffee Commercial Ad",
                slug="coffee-commercial-ad",
                album="Commercials 2026",
                tools_used="Gemini, Runway",
                duration="0:30",
                featured=True,
                visibility="published"
            )
            db.session.add_all([v1, v2, v3])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login_admin(self):
        return self.client.post("/auth/login", data={
            "username": "admin",
            "password": "adminpass"
        }, follow_redirects=True)

    def test_video_studio_public_albums(self):
        response = self.client.get("/video-studio")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"AI CREATIVE VIDEO STUDIO", response.data)
        self.assertIn(b"Kung Fu Chronicles", response.data)
        self.assertIn(b"Commercials 2026", response.data)
        self.assertIn(b"AI Kung Fu Scene", response.data)
        self.assertIn(b"Coffee Commercial Ad", response.data)
        # Check album pill count
        self.assertIn(b"Kung Fu Chronicles (2)", response.data)
        self.assertIn(b"Commercials 2026 (1)", response.data)

    def test_admin_create_video_with_album(self):
        self.login_admin()
        res = self.client.post("/admin/videos/create", data={
            "title": "Cyberpunk Drone Chase",
            "album": "Sci-Fi Action",
            "category": "AI Creative",
            "tools_used": "Gemini, After Effects",
            "duration": "0:20",
            "aspect_ratio": "16:9",
            "visibility": "published"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Cyberpunk Drone Chase", res.data)
        self.assertIn(b"Sci-Fi Action", res.data)

        with self.app.app_context():
            v = Video.query.filter_by(title="Cyberpunk Drone Chase").first()
            self.assertIsNotNone(v)
            self.assertEqual(v.album, "Sci-Fi Action")

    def test_admin_edit_video_album(self):
        self.login_admin()
        with self.app.app_context():
            v = Video.query.filter_by(slug="coffee-commercial-ad").first()
            v_id = v.id

        res = self.client.post(f"/admin/videos/edit/{v_id}", data={
            "title": "Coffee Commercial Ad Extended",
            "album": "Premium Brand Series",
            "category": "Commercial",
            "tools_used": "Gemini, Premier Pro",
            "duration": "0:45",
            "aspect_ratio": "16:9",
            "visibility": "published"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"updated successfully", res.data)

        with self.app.app_context():
            updated = db.session.get(Video, v_id)
            self.assertEqual(updated.title, "Coffee Commercial Ad Extended")
            self.assertEqual(updated.album, "Premium Brand Series")

    def test_admin_filter_by_album(self):
        self.login_admin()
        res = self.client.get("/admin/videos/?album=Kung Fu Chronicles")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"AI Kung Fu Scene", res.data)
        self.assertIn(b"AI Kung Fu Finale", res.data)
        self.assertNotIn(b"Coffee Commercial Ad", res.data)

if __name__ == "__main__":
    unittest.main()
