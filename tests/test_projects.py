import unittest
from app import create_app
from app.models import db, Project

class ProjectsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            p = Project(
                title="PAWSHOP Command Center",
                slug="pawshop-test",
                status_badge="Live",
                technologies="Python, Flask, MySQL",
                visibility="published",
                featured=True
            )
            db.session.add(p)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_homepage_shows_project(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PAWSHOP Command Center", response.data)
        self.assertIn(b"DIGITAL", response.data)
        self.assertIn(b"COMMAND", response.data)

    def test_project_detail_renders(self):
        response = self.client.get("/projects/pawshop-test")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PROJECT DOSSIER", response.data)

if __name__ == "__main__":
    unittest.main()
