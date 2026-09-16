import io
import os
import unittest
from app import create_app
from app.models import db, User, SiteSetting

class ResumeTestCase(unittest.TestCase):
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

    def test_resume_fallback_when_not_configured(self):
        # When resume is empty, /resume should redirect to /files
        res = self.client.get("/resume", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/files", res.headers["Location"])

    def test_admin_upload_pdf_resume_and_download(self):
        # 1. Login as admin
        self.client.post("/auth/login", data={
            "username": "admin",
            "password": "adminpass"
        }, follow_redirects=True)

        # 2. Upload dummy PDF resume
        pdf_content = b"%PDF-1.4 simulated resume document binary stream"
        data = {
            "display_name": "Richard Ong",
            "resume": (io.BytesIO(pdf_content), "richard_ong_resume.pdf")
        }
        res = self.client.post("/admin/settings", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            settings = SiteSetting.get_settings()
            self.assertTrue(settings.resume_url.startswith("/uploads/documents/"))
            self.assertTrue(settings.resume_url.endswith(".pdf"))
            saved_resume_url = settings.resume_url

        # 3. Test public /resume route serves the file as attachment
        download_res = self.client.get("/resume")
        self.assertEqual(download_res.status_code, 200)
        self.assertEqual(download_res.data, pdf_content)
        self.assertIn("attachment", download_res.headers.get("Content-Disposition", ""))
        download_res.close()

        # 4. Verify home page has the download link
        home_res = self.client.get("/")
        self.assertEqual(home_res.status_code, 200)
        self.assertIn(b"/resume", home_res.data)

        # Clean up uploaded file
        with self.app.app_context():
            rel_path = saved_resume_url.replace("/uploads/", "")
            full_path = os.path.join(self.app.config["UPLOAD_FOLDER"], rel_path)
            if os.path.exists(full_path):
                os.remove(full_path)

    def test_admin_set_external_resume_url(self):
        # 1. Login as admin
        self.client.post("/auth/login", data={
            "username": "admin",
            "password": "adminpass"
        }, follow_redirects=True)

        # 2. Set external resume cloud URL
        external_url = "https://drive.google.com/file/d/1A2B3C4D5E/view?usp=sharing"
        res = self.client.post("/admin/settings", data={
            "display_name": "Richard Ong",
            "resume_url_text": external_url
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            settings = SiteSetting.get_settings()
            self.assertEqual(settings.resume_url, external_url)

        # 3. /resume should redirect to the external URL
        download_res = self.client.get("/resume", follow_redirects=False)
        self.assertEqual(download_res.status_code, 302)
        self.assertEqual(download_res.headers["Location"], external_url)

    def test_admin_clear_resume(self):
        # 1. Login as admin
        self.client.post("/auth/login", data={
            "username": "admin",
            "password": "adminpass"
        }, follow_redirects=True)

        # 2. First set an external link
        self.client.post("/admin/settings", data={
            "resume_url_text": "https://example.com/cv.pdf"
        }, follow_redirects=True)

        with self.app.app_context():
            settings = SiteSetting.get_settings()
            self.assertEqual(settings.resume_url, "https://example.com/cv.pdf")

        # 3. Clear resume
        self.client.post("/admin/settings", data={
            "clear_resume": "1"
        }, follow_redirects=True)

        with self.app.app_context():
            settings = SiteSetting.get_settings()
            self.assertEqual(settings.resume_url, "")

        # 4. Now /resume should redirect to /files
        download_res = self.client.get("/resume", follow_redirects=False)
        self.assertEqual(download_res.status_code, 302)
        self.assertIn("/files", download_res.headers["Location"])

if __name__ == "__main__":
    unittest.main()
