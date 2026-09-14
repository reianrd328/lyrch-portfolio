import unittest
import json
from unittest.mock import patch, MagicMock
from app import create_app
from app.models import db, User, SiteSetting
from app.services.gdrive_service import clean_folder_id, is_gdrive_configured, upload_backup_to_gdrive

class GDriveTestCase(unittest.TestCase):
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
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self):
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(self.admin.id)
            sess["_fresh"] = True

    def test_clean_folder_id(self):
        """Test URL parsing for folder ID extraction."""
        self.assertEqual(clean_folder_id("1BxiMVs0XRA5nFMdKvBHKGo24xpVTk9-F"), "1BxiMVs0XRA5nFMdKvBHKGo24xpVTk9-F")
        self.assertEqual(
            clean_folder_id("https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBHKGo24xpVTk9-F?usp=sharing"),
            "1BxiMVs0XRA5nFMdKvBHKGo24xpVTk9-F"
        )
        self.assertEqual(
            clean_folder_id("https://drive.google.com/drive/folders/ABC_123/"),
            "ABC_123"
        )
        self.assertEqual(clean_folder_id(""), "")

    def test_gdrive_settings_persistence(self):
        """Test that Google Drive settings persist via admin settings form."""
        self.login()
        res = self.client.post("/admin/settings", data={
            "display_name": "DROP FARMD",
            "job_title": "IT SUPPORT",
            "gdrive_backup_enabled": "on",
            "gdrive_folder_id": "https://drive.google.com/drive/folders/1ABC_MY_FOLDER?usp=sharing"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        settings = SiteSetting.get_settings()
        self.assertTrue(settings.gdrive_backup_enabled)
        self.assertEqual(settings.gdrive_folder_id, "1ABC_MY_FOLDER")

    def test_manual_upload_unconfigured_error_handling(self):
        """Test POST /admin/backup/upload-gdrive handles unconfigured credentials safely."""
        self.login()
        res = self.client.post("/admin/backup/upload-gdrive", follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        settings = SiteSetting.get_settings()
        self.assertIn("Failed (Google Drive)", settings.backup_last_status)

    @patch("app.services.gdrive_service.is_gdrive_configured", return_value=True)
    @patch("app.services.gdrive_service.get_drive_service")
    def test_mocked_gdrive_successful_upload(self, mock_get_service, mock_is_configured):
        """Test successful Google Drive upload logic with mocked Drive API service."""
        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_create = MagicMock()

        mock_create.execute.return_value = {
            "id": "file-xyz-789",
            "name": "lyrch_backup_test.json",
            "webViewLink": "https://drive.google.com/file/d/file-xyz-789/view"
        }
        mock_files.create.return_value = mock_create
        mock_service.files.return_value = mock_files
        mock_get_service.return_value = mock_service

        success, msg, link = upload_backup_to_gdrive(
            backup_json_str='{"test": 123}',
            filename="lyrch_backup_test.json",
            folder_id="target_folder_123"
        )
        self.assertTrue(success)
        self.assertIn("Successfully uploaded", msg)
        self.assertEqual(link, "https://drive.google.com/file/d/file-xyz-789/view")

    @patch("app.services.gdrive_service.is_gdrive_configured", return_value=True)
    @patch("app.services.gdrive_service.get_drive_service")
    def test_cron_triggers_gdrive_backup(self, mock_get_service, mock_is_configured):
        """Test that daily cron triggers Google Drive upload when enabled."""
        settings = SiteSetting.get_settings()
        settings.gdrive_backup_enabled = True
        settings.gdrive_folder_id = "folder_auto_cron"
        db.session.commit()

        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_create = MagicMock()
        mock_create.execute.return_value = {
            "id": "file-cron-123",
            "name": "lyrch_backup_cron.json",
            "webViewLink": "https://drive.google.com/file/d/file-cron-123/view"
        }
        mock_files.create.return_value = mock_create
        mock_service.files.return_value = mock_files
        mock_get_service.return_value = mock_service

        token = self.app.config.get("SECRET_KEY")
        res = self.client.get(f"/api/cron/daily-backup?token={token}")
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("Google Drive: Uploaded", data.get("message"))

if __name__ == "__main__":
    unittest.main()
