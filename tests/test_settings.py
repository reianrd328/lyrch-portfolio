import unittest
from app import create_app
from app.models import db, User, SiteSetting

class SettingsTestCase(unittest.TestCase):
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
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_default_settings_on_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"DROP FARMD", response.data)
        self.assertIn(b"IT SUPPORT SPECIALIST", response.data)
        self.assertIn(b'data-theme="cyber"', response.data)

    def test_settings_require_login(self):
        response = self.client.get("/admin/settings")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_update_settings_as_admin(self):
        # 1. Login
        self.client.post("/auth/login", data={
            "username": "admin",
            "password": "adminpass"
        }, follow_redirects=True)

        # 2. Post updated settings
        response = self.client.post("/admin/settings", data={
            "display_name": "ALEX RIVERA",
            "job_title": "CLOUD ARCHITECT & AI ENGINEER",
            "location": "Tokyo, Japan",
            "hero_pretitle": "GREETINGS FROM",
            "hero_title": "NEO COMMAND CORE",
            "hero_tags": "ARCHITECT • DEVOPS • AI",
            "hero_bio": "Passionate builder creating resilient infrastructure and generative tools.",
            "metric1_num": "12+",
            "metric1_title": "Years Cloud",
            "metric1_desc": "Enterprise Infrastructure",
            "metric2_num": "50+",
            "metric2_title": "Clusters Managed",
            "metric2_desc": "Global Multi-Region",
            "metric3_num": "500+",
            "metric3_title": "Microservices",
            "metric3_desc": "Kubernetes Orchestrated",
            "metric4_num": "99.99%",
            "metric4_title": "Uptime SLA",
            "metric4_desc": "Mission Critical",
            "metric5_num": "Constantly Innovating",
            "metric5_title": "",
            "metric5_desc": "Agentic AI Operations",
            "map_stat1_num": "50+",
            "map_stat1_label": "DATA CENTERS",
            "map_stat2_num": "500M+",
            "map_stat2_label": "REQUESTS DAILY",
            "map_stat3_num": "12+",
            "map_stat3_label": "YEARS ENGINEERING",
            "map_tagline": "Architecting the Future",
            "quote_text": "Automation is the key to scalability.",
            "quote_signature": "Alex R.",
            "footer_motto": "CODE → DEPLOY → SCALE → AUTOMATE",
            "footer_sub": "NEXT-GEN CLOUD PLATFORMS",
            "copyright_text": "\u00a9 2026 ALEX RIVERA All rights reserved.",
            "github_url": "https://github.com/alexrivera",
            "linkedin_url": "https://linkedin.com/in/alexrivera",
            "youtube_url": "https://youtube.com/@alexrivera",
            "facebook_url": "https://facebook.com/alexrivera",
            "contact_email": "alex@rivera.dev",
            "default_theme": "synthwave"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Command Center Dashboard &amp; System Settings Updated!", response.data)

        # 3. Verify public homepage reflects changes
        home_res = self.client.get("/")
        self.assertEqual(home_res.status_code, 200)
        self.assertIn(b"ALEX RIVERA", home_res.data)
        self.assertIn(b"CLOUD ARCHITECT &amp; AI ENGINEER", home_res.data)
        self.assertIn(b'data-theme="synthwave"', home_res.data)
        self.assertIn(b"12+", home_res.data)
        self.assertIn(b"https://github.com/alexrivera", home_res.data)
        self.assertIn(b"alex@rivera.dev", home_res.data)
        self.assertIn(b"Alex R.", home_res.data)

    def test_custom_colors_and_avatar_upload(self):
        import io
        # 1. Login
        self.client.post("/auth/login", data={
            "username": "admin",
            "password": "adminpass"
        }, follow_redirects=True)

        # 2. Upload fake avatar image and custom colors
        avatar_file = (io.BytesIO(b"fake image content for testing"), "my_avatar.png")
        response = self.client.post("/admin/settings", data={
            "display_name": "SARAH CONNER",
            "job_title": "CYBERNETIC DEFENSE SPECIALIST",
            "default_theme": "custom",
            "custom_primary_color": "#ff5500",
            "custom_secondary_color": "#00ffcc",
            "avatar": avatar_file
        }, content_type="multipart/form-data", follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        # 3. Verify settings in database
        with self.app.app_context():
            s = SiteSetting.get_settings()
            self.assertEqual(s.default_theme, "custom")
            self.assertEqual(s.custom_primary_color, "#ff5500")
            self.assertEqual(s.custom_secondary_color, "#00ffcc")
            self.assertTrue(s.avatar_url.startswith("/uploads/profile/"))
            self.assertTrue(s.avatar_url.endswith(".png"))

        # 4. Verify homepage reflects custom colors & avatar
        home_res = self.client.get("/")
        self.assertEqual(home_res.status_code, 200)
        self.assertIn(b'data-theme="custom"', home_res.data)
        self.assertIn(b"#ff5500", home_res.data)
        self.assertIn(b"#00ffcc", home_res.data)
        self.assertIn(b"/uploads/profile/", home_res.data)

    def test_contact_page_dynamic_settings(self):
        # 1. Check default values on /contact
        res = self.client.get("/contact")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Initiate Connection", res.data)
        self.assertIn(b"Available for Select Contracts", res.data)
        self.assertIn(b"Philippines", res.data)

        # 2. Login as admin and update contact settings
        self.client.post("/auth/login", data={
            "username": "admin",
            "password": "adminpass"
        }, follow_redirects=True)

        self.client.post("/admin/settings", data={
            "contact_title": "Get In Touch With Chad",
            "contact_status": "Accepting High-Impact Projects",
            "contact_description": "Direct communications line for custom AI and enterprise architecture.",
            "contact_email": "chad@customdomain.io",
            "location": "Metro Manila, PH",
            "github_url": "https://github.com/chadofficial",
            "facebook_url": "https://facebook.com/chadofficial"
        }, follow_redirects=True)

        # 3. Check updated values on /contact
        res2 = self.client.get("/contact")
        self.assertEqual(res2.status_code, 200)
        self.assertIn(b"Get In Touch With Chad", res2.data)
        self.assertIn(b"Accepting High-Impact Projects", res2.data)
        self.assertIn(b"Direct communications line for custom AI and enterprise architecture.", res2.data)
        self.assertIn(b"chad@customdomain.io", res2.data)
        self.assertIn(b"Metro Manila, PH", res2.data)
        self.assertIn(b"https://github.com/chadofficial", res2.data)
        self.assertIn(b"https://facebook.com/chadofficial", res2.data)

if __name__ == "__main__":
    unittest.main()
