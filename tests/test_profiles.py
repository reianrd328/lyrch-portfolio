import io
import json
import unittest
from app import create_app
from app.models import db, User, SiteSetting, Project, Skill, PortfolioProfile
from app.services.profile_service import (
    bootstrap_default_profile_if_needed,
    switch_active_profile,
    capture_current_portfolio_dict
)

class PortfolioProfilesTestCase(unittest.TestCase):
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
            settings = SiteSetting.get_settings()
            settings.display_name = "DROP FARMD"
            settings.default_theme = "cyber"

            # Add a sample project to initial portfolio
            p = Project(
                title="DROP FARMD Core System",
                slug="drop-farmd-core",
                category="Software Project",
                status_badge="Live",
                featured=True,
                visibility="published",
                technologies="Python, Flask"
            )
            db.session.add(p)
            db.session.commit()

            # Bootstrap master profile
            bootstrap_default_profile_if_needed()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login_admin(self):
        return self.client.post("/auth/login", data={
            "username": "admin",
            "password": "adminpass"
        }, follow_redirects=True)

    def test_bootstrap_initial_profile(self):
        with self.app.app_context():
            master = PortfolioProfile.query.filter_by(is_active=True).first()
            self.assertIsNotNone(master)
            self.assertIn("DROP FARMD", master.name)
            self.assertEqual(master.slug, "drop-farmd")
            self.assertTrue(master.is_active)
            data = master.get_data()
            self.assertIn("projects", data)
            self.assertEqual(len(data["projects"]), 1)
            self.assertEqual(data["projects"][0]["title"], "DROP FARMD Core System")

    def test_profiles_hub_requires_auth(self):
        response = self.client.get("/admin/profiles")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_view_profiles_as_admin(self):
        self.login_admin()
        response = self.client.get("/admin/profiles")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PORTFOLIO PROFILES", response.data)
        self.assertIn(b"DROP FARMD (Master Portfolio)", response.data)
        self.assertIn(b"CURRENTLY LIVE ON MAIN WEBSITE", response.data)

    def test_create_new_starter_profile(self):
        self.login_admin()
        response = self.client.post("/admin/profiles/create", data={
            "name": "Apex Construction Showcase",
            "client_name": "Apex Corp",
            "slug": "apex-corp",
            "theme_preset": "matrix",
            "template_type": "starter",
            "description": "Commercial builder portfolio"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Apex Construction Showcase", response.data)
        self.assertIn(b"/p/apex-corp", response.data)

        with self.app.app_context():
            profile = PortfolioProfile.query.filter_by(slug="apex-corp").first()
            self.assertIsNotNone(profile)
            self.assertFalse(profile.is_active)
            self.assertEqual(profile.client_name, "Apex Corp")
            self.assertEqual(profile.theme_preset, "matrix")
            data = profile.get_data()
            self.assertGreaterEqual(len(data.get("projects", [])), 1)

    def test_create_clone_profile(self):
        self.login_admin()
        response = self.client.post("/admin/profiles/create", data={
            "name": "DROP FARMD v2",
            "client_name": "Lyrch Studio",
            "slug": "drop-farmd-v2",
            "theme_preset": "synthwave",
            "template_type": "clone",
            "description": "Cloned backup of current site"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            clone = PortfolioProfile.query.filter_by(slug="drop-farmd-v2").first()
            self.assertIsNotNone(clone)
            self.assertFalse(clone.is_active)
            data = clone.get_data()
            self.assertEqual(len(data.get("projects", [])), 1)
            self.assertEqual(data["projects"][0]["slug"], "drop-farmd-core")

    def test_switch_profile_and_verify_zero_data_loss(self):
        self.login_admin()
        # 1. Create a client profile
        self.client.post("/admin/profiles/create", data={
            "name": "Dr. Jane Smith Dental",
            "client_name": "Dr. Jane Smith",
            "slug": "dr-jane",
            "theme_preset": "cobalt",
            "template_type": "starter",
            "description": "Dental clinic showcase"
        })

        with self.app.app_context():
            client_prof = PortfolioProfile.query.filter_by(slug="dr-jane").first()
            client_id = client_prof.id

        # 2. Activate Dr. Jane Smith profile
        response = self.client.post(f"/admin/profiles/{client_id}/activate", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Portfolio successfully switched to", response.data)

        # 3. Check live website: it should now show Dr. Jane's settings!
        home_res = self.client.get("/")
        self.assertEqual(home_res.status_code, 200)
        self.assertIn(b"Dr. Jane Smith", home_res.data)

        # 4. Check DB state: active profile is Dr. Jane
        with self.app.app_context():
            active = PortfolioProfile.query.filter_by(is_active=True).first()
            self.assertEqual(active.id, client_id)

            # Master profile (DROP FARMD) is now inactive but its data is 100% saved
            master = PortfolioProfile.query.filter_by(slug="drop-farmd").first()
            self.assertFalse(master.is_active)
            master_data = master.get_data()
            self.assertEqual(len(master_data["projects"]), 1)
            self.assertEqual(master_data["projects"][0]["slug"], "drop-farmd-core")
            master_id = master.id

        # 5. Switch back to DROP FARMD Master Profile
        switch_back = self.client.post(f"/admin/profiles/{master_id}/activate", follow_redirects=True)
        self.assertEqual(switch_back.status_code, 200)

        # 6. Verify master site restored 100%
        home_restored = self.client.get("/")
        self.assertEqual(home_restored.status_code, 200)
        self.assertIn(b"DROP FARMD", home_restored.data)

    def test_standalone_client_preview_url(self):
        self.login_admin()
        # Create a client profile
        self.client.post("/admin/profiles/create", data={
            "name": "Nexus Robotics",
            "client_name": "Nexus Corp",
            "slug": "nexus-robotics",
            "theme_preset": "matrix",
            "template_type": "starter",
            "description": "Robotics engineering portfolio"
        })

        # Master site is still DROP FARMD
        main_home = self.client.get("/")
        self.assertIn(b"DROP FARMD", main_home.data)

        # Standalone dedicated link /p/nexus-robotics renders Nexus Robotics
        preview_res = self.client.get("/p/nexus-robotics")
        self.assertEqual(preview_res.status_code, 200)
        self.assertIn(b"DEDICATED CLIENT PREVIEW", preview_res.data)
        self.assertIn(b"Nexus Robotics", preview_res.data)
        self.assertIn(b"Nexus Corp", preview_res.data)

        # Check sub-pages
        about_res = self.client.get("/p/nexus-robotics/about")
        self.assertEqual(about_res.status_code, 200)
        self.assertIn(b"DEDICATED CLIENT PREVIEW", about_res.data)

        projects_res = self.client.get("/p/nexus-robotics/projects")
        self.assertEqual(projects_res.status_code, 200)
        self.assertIn(b"DEDICATED CLIENT PREVIEW", projects_res.data)

    def test_export_and_import_profile(self):
        self.login_admin()
        with self.app.app_context():
            master = PortfolioProfile.query.filter_by(slug="drop-farmd").first()
            master_id = master.id

        # Export JSON
        export_res = self.client.get(f"/admin/profiles/{master_id}/export")
        self.assertEqual(export_res.status_code, 200)
        self.assertIn("application/json", export_res.headers["Content-Type"])
        exported_payload = json.loads(export_res.data)
        self.assertIn("content", exported_payload)
        self.assertEqual(exported_payload["profile"]["slug"], "drop-farmd")

        # Import as a new profile
        exported_payload["profile"]["name"] = "Imported Client Showcase"
        exported_payload["profile"]["client_name"] = "Acme Global"
        json_file = io.BytesIO(json.dumps(exported_payload).encode("utf-8"))

        import_res = self.client.post("/admin/profiles/import", data={
            "profile_file": (json_file, "client_portfolio.json")
        }, follow_redirects=True)

        self.assertEqual(import_res.status_code, 200)
        self.assertIn(b"Imported Client Showcase", import_res.data)

        with self.app.app_context():
            imported = PortfolioProfile.query.filter_by(name="Imported Client Showcase").first()
            self.assertIsNotNone(imported)
            self.assertEqual(imported.client_name, "Acme Global")

    def test_cannot_delete_active_profile(self):
        self.login_admin()
        with self.app.app_context():
            master = PortfolioProfile.query.filter_by(is_active=True).first()
            master_id = master.id

        # Attempt to delete active profile
        del_res = self.client.post(f"/admin/profiles/{master_id}/delete", follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertIn(b"Cannot delete the currently active portfolio profile", del_res.data)

        # Verify profile still exists
        with self.app.app_context():
            still_there = db.session.get(PortfolioProfile, master_id)
            self.assertIsNotNone(still_there)

if __name__ == "__main__":
    unittest.main()
