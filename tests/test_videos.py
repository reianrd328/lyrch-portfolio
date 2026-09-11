import unittest
from app import create_app
from app.models import db, Video

class VideoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            v = Video(
                title="AI Kung Fu Scene",
                slug="ai-kung-fu-scene",
                tools_used="Gemini, Video Edit",
                duration="0:10",
                featured=True,
                visibility="published"
            )
            db.session.add(v)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_video_studio_page(self):
        response = self.client.get("/video-studio")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"AI CREATIVE VIDEO STUDIO", response.data)
        self.assertIn(b"AI Kung Fu Scene", response.data)

if __name__ == "__main__":
    unittest.main()

