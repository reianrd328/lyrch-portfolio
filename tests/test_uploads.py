import unittest
from app import create_app
from app.services.upload_service import allowed_file

class UploadsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")

    def test_allowed_file_types(self):
        images = {"png", "jpg", "jpeg", "webp"}
        self.assertTrue(allowed_file("screenshot.png", images))
        self.assertTrue(allowed_file("hero.JPG", images))
        self.assertFalse(allowed_file("payload.exe", images))
        self.assertFalse(allowed_file("script.sh", images))

if __name__ == "__main__":
    unittest.main()

