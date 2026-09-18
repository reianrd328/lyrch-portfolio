import unittest
from app import create_app
from app.models import db, User, Experience, SiteSetting

class ExperienceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # Create admin user
            u = User(username="admin", email="admin@lyrch.dev")
            u.set_password("adminpass")
            db.session.add(u)
            # Create default settings
            SiteSetting.get_settings()

            # Seed test experiences
            e1 = Experience(
                role_title="Senior IT Support Specialist & Systems Administrator",
                company="Nationwide Multi-Branch Support",
                location="Philippines",
                period="2018 — Present",
                description="Orchestrating hardware, networking, and software systems across 100+ branches.",
                order_index=1
            )
            e2 = Experience(
                role_title="IT Infrastructure & Technical Support Engineer",
                company="Corporate IT Operations",
                location="Philippines",
                period="2012 — 2018",
                description="Delivered Level 2/3 technical diagnostics.",
                order_index=2
            )
            db.session.add_all([e1, e2])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _login(self):
        return self.client.post("/auth/login", data={
            "username": "admin",
            "password": "adminpass"
        }, follow_redirects=True)

    def test_public_experience_page_renders_database_records(self):
        res = self.client.get("/experience")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Senior IT Support Specialist", res.data)
        self.assertIn(b"Nationwide Multi-Branch Support", res.data)
        self.assertIn(b"IT Infrastructure &amp; Technical Support Engineer", res.data)

    def test_admin_experience_list(self):
        self._login()
        res = self.client.get("/admin/experience/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Senior IT Support Specialist", res.data)
        self.assertIn(b"Edit", res.data)

    def test_admin_edit_experience(self):
        self._login()
        with self.app.app_context():
            e = Experience.query.filter_by(order_index=1).first()
            e_id = e.id

        # GET edit page
        get_res = self.client.get(f"/admin/experience/edit/{e_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertIn(b"Senior IT Support Specialist", get_res.data)

        # POST updated experience
        post_res = self.client.post(f"/admin/experience/edit/{e_id}", data={
            "role_title": "Lead Principal Cloud Systems Architect",
            "company": "Enterprise Global Cloud Corp",
            "location": "Tokyo & Remote",
            "period": "2020 — Present",
            "description": "Designing high-scale Kubernetes clusters and AI agents.",
            "highlights": "Saved $1.2M in annual cloud costs\nZero downtime across 3 years",
            "order_index": "1"
        }, follow_redirects=True)
        self.assertEqual(post_res.status_code, 200)

        # Check DB updated
        with self.app.app_context():
            updated = db.session.get(Experience, e_id)
            self.assertEqual(updated.role_title, "Lead Principal Cloud Systems Architect")
            self.assertEqual(updated.company, "Enterprise Global Cloud Corp")
            self.assertEqual(updated.location, "Tokyo & Remote")
            self.assertEqual(len(updated.highlights_list), 2)

        # Check public page reflects the update
        pub_res = self.client.get("/experience")
        self.assertEqual(pub_res.status_code, 200)
        self.assertIn(b"Lead Principal Cloud Systems Architect", pub_res.data)
        self.assertIn(b"Enterprise Global Cloud Corp", pub_res.data)
        self.assertIn(b"Saved $1.2M in annual cloud costs", pub_res.data)

    def test_admin_create_and_delete_experience(self):
        self._login()
        # Verify GET create page has the new fields
        get_res = self.client.get("/admin/experience/create")
        self.assertEqual(get_res.status_code, 200)
        self.assertIn(b"KEY HIGHLIGHTS &amp; BULLET POINTS", get_res.data)
        self.assertIn(b"DISPLAY ORDER PRIORITY", get_res.data)

        create_res = self.client.post("/admin/experience/create", data={
            "role_title": "Junior IT Technician",
            "company": "Local Tech Solutions",
            "location": "Cebu, Philippines",
            "period": "2006 — 2008",
            "description": "Hardware repair and workstation deployment.",
            "highlights": "Assembled 50+ desktop units\nAssisted senior engineers on site",
            "order_index": "3"
        }, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)

        with self.app.app_context():
            new_exp = Experience.query.filter_by(role_title="Junior IT Technician").first()
            self.assertIsNotNone(new_exp)
            self.assertEqual(new_exp.order_index, 3)
            self.assertEqual(len(new_exp.highlights_list), 2)
            self.assertIn("Assembled 50+ desktop units", new_exp.highlights)
            new_id = new_exp.id

        # Delete it
        del_res = self.client.post(f"/admin/experience/delete/{new_id}", follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        with self.app.app_context():
            deleted = db.session.get(Experience, new_id)
            self.assertIsNone(deleted)

if __name__ == "__main__":
    unittest.main()

