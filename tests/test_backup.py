import unittest
import json
import io
from app import create_app
from app.models import db, User, SiteSetting, Project
from app.services.backup_service import export_database_to_dict, restore_database_from_dict

class BackupTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Create test admin
        self.admin = User(username="admin", email="admin@lyrch.dev")
        self.admin.set_password("admin123")
        db.session.add(self.admin)
        
        # Create test project
        self.project = Project(
            title="Backup Test Project",
            slug="backup-test-project",
            category="Testing",
            short_description="Testing backup service."
        )
        db.session.add(self.project)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self):
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(self.admin.id)
            sess["_fresh"] = True

    def test_export_database_structure(self):
        """Test that export_database_to_dict returns valid schema and record counts."""
        backup = export_database_to_dict()
        self.assertIn("metadata", backup)
        self.assertIn("tables", backup)
        self.assertIn("projects", backup["tables"])
        self.assertIn("users", backup["tables"])
        self.assertGreaterEqual(len(backup["tables"]["projects"]), 1)
        self.assertEqual(backup["tables"]["projects"][0]["slug"], "backup-test-project")

    def test_backup_download_endpoint(self):
        """Test GET /admin/backup/download streams valid JSON file."""
        self.login()
        res = self.client.get("/admin/backup/download")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/json")
        self.assertIn("attachment", res.headers.get("Content-Disposition", ""))
        
        data = json.loads(res.data.decode("utf-8"))
        self.assertIn("tables", data)
        self.assertIn("projects", data["tables"])

    def test_backup_settings_persistence(self):
        """Test that backup toggle and email persist in SiteSettings."""
        self.login()
        res = self.client.post("/admin/settings", data={
            "display_name": "DROP FARMD",
            "job_title": "IT SUPPORT",
            "backup_auto_enabled": "on",
            "backup_email": "backup@lyrch.dev",
            "backup_frequency": "daily"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        settings = SiteSetting.get_settings()
        self.assertTrue(settings.backup_auto_enabled)
        self.assertEqual(settings.backup_email, "backup@lyrch.dev")

    def test_cron_endpoint_security(self):
        """Test that cron endpoint requires valid token."""
        # Missing token -> 403
        res = self.client.get("/api/cron/daily-backup")
        self.assertEqual(res.status_code, 403)

        # Valid token with backup toggled OFF
        token = self.app.config.get("SECRET_KEY")
        res = self.client.get(f"/api/cron/daily-backup?token={token}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "skipped")

    def test_restore_database(self):
        """Test restore_database_from_dict properly imports records."""
        sample_backup = {
            "metadata": {"version": "1.0"},
            "tables": {
                "projects": [{
                    "title": "Restored Project",
                    "slug": "restored-project",
                    "category": "Disaster Recovery",
                    "short_description": "Restored from cloud archive."
                }],
                "site_settings": [{
                    "display_name": "RESTORED COMMANDER",
                    "job_title": "LEAD ARCHITECT"
                }]
            }
        }
        success, msg = restore_database_from_dict(sample_backup)
        self.assertTrue(success)

        p = Project.query.filter_by(slug="restored-project").first()
        self.assertIsNotNone(p)
        self.assertEqual(p.title, "Restored Project")

        s = SiteSetting.get_settings()
        self.assertEqual(s.display_name, "RESTORED COMMANDER")

if __name__ == "__main__":
    unittest.main()

