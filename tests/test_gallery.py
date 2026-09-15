import unittest
from app import create_app
from app.models import db, GalleryItem, Project, User
from app.services.storage_service import format_bytes, get_storage_stats

class GalleryTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            u = User(username="admin", email="admin@lyrch.dev")
            u.set_password("adminpass")
            db.session.add(u)

            p1 = Project(title="Cyberpunk Dashboard", slug="cyberpunk-dashboard", category="Web App")
            p2 = Project(title="PawShop Mobile", slug="pawshop-mobile", category="Mobile App")
            db.session.add_all([p1, p2])
            db.session.flush()

            item1 = GalleryItem(
                title="HUD Analytics Interface",
                category="UI / UX",
                project_id=p1.id,
                description="Dark neon analytical command deck",
                tags="hud, cyber, dashboard",
                visibility="published",
                image_url="/static/images/placeholder.jpg",
                file_size_bytes=1024 * 500
            )
            item2 = GalleryItem(
                title="PawShop Checkout Flow",
                category="Screenshots",
                project_id=p2.id,
                description="User checkout flow for pet store",
                tags="mobile, e-commerce",
                visibility="draft",
                image_url="/static/images/placeholder.jpg",
                file_size_bytes=1024 * 800
            )
            item3 = GalleryItem(
                title="Secret Neon Graphic Asset",
                category="Graphics",
                project_id=None,
                description="Unreleased vector asset",
                tags="vector, glow",
                visibility="private",
                image_url="/static/images/placeholder.jpg",
                file_size_bytes=1024 * 300
            )
            db.session.add_all([item1, item2, item3])
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

    def test_gallery_model_and_tags(self):
        with self.app.app_context():
            item = GalleryItem.query.filter_by(title="HUD Analytics Interface").first()
            self.assertIsNotNone(item)
            self.assertEqual(item.project.title, "Cyberpunk Dashboard")
            self.assertIn("hud", item.tags_list)
            self.assertIn("cyber", item.tags_list)
            self.assertEqual(item.visibility, "published")
            self.assertEqual(item.file_size_formatted, "500.0 KB")
            
            d = item.to_dict()
            self.assertEqual(d["title"], "HUD Analytics Interface")
            self.assertEqual(d["project_title"], "Cyberpunk Dashboard")
            self.assertEqual(d["visibility"], "published")

    def test_storage_service(self):
        self.assertEqual(format_bytes(0), "0 MB")
        self.assertEqual(format_bytes(500 * 1024), "500.0 KB")
        self.assertEqual(format_bytes(5 * 1024 * 1024), "5.0 MB")
        self.assertEqual(format_bytes(2 * 1024 * 1024 * 1024), "2.0 GB")

        with self.app.app_context():
            stats = get_storage_stats()
            self.assertIn("images_formatted", stats)
            self.assertIn("videos_formatted", stats)
            self.assertIn("docs_formatted", stats)
            self.assertIn("total_formatted", stats)

    def test_admin_gallery_index(self):
        self.login_admin()
        res = self.client.get("/admin/gallery/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"CREATIVE ASSET LIBRARY", res.data)
        self.assertIn(b"HUD Analytics Interface", res.data)
        self.assertIn(b"PawShop Checkout Flow", res.data)
        self.assertIn(b"Secret Neon Graphic Asset", res.data)
        # Verify telemetry stats
        self.assertIn(b"Total Assets", res.data)

    def test_admin_gallery_filters(self):
        self.login_admin()
        
        # Filter by category
        res = self.client.get("/admin/gallery/?cat=UI+%2F+UX")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"HUD Analytics Interface", res.data)
        self.assertNotIn(b"PawShop Checkout Flow", res.data)

        # Filter by status
        res = self.client.get("/admin/gallery/?status=draft")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"PawShop Checkout Flow", res.data)
        self.assertNotIn(b"HUD Analytics Interface", res.data)

        # Filter by search query
        res = self.client.get("/admin/gallery/?q=Secret")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Secret Neon Graphic Asset", res.data)
        self.assertNotIn(b"HUD Analytics Interface", res.data)

    def test_admin_gallery_api_item(self):
        self.login_admin()
        with self.app.app_context():
            item = GalleryItem.query.filter_by(title="HUD Analytics Interface").first()
            item_id = item.id

        res = self.client.get(f"/admin/gallery/api/item/{item_id}")
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["item"]["title"], "HUD Analytics Interface")
        self.assertEqual(json_data["item"]["category"], "UI / UX")

    def test_admin_gallery_edit(self):
        self.login_admin()
        with self.app.app_context():
            item = GalleryItem.query.filter_by(title="HUD Analytics Interface").first()
            item_id = item.id

        # Update via JSON
        res = self.client.post(
            f"/admin/gallery/edit/{item_id}",
            json={
                "title": "Renamed Analytics UI",
                "category": "Branding",
                "visibility": "private",
                "tags": "updated, tag"
            }
        )
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data["success"])

        with self.app.app_context():
            updated = db.session.get(GalleryItem, item_id)
            self.assertEqual(updated.title, "Renamed Analytics UI")
            self.assertEqual(updated.category, "Branding")
            self.assertEqual(updated.visibility, "private")

    def test_gallery_custom_project_creation(self):
        self.login_admin()
        with self.app.app_context():
            item = GalleryItem.query.filter_by(title="Secret Neon Graphic Asset").first()
            item_id = item.id

        # Edit and assign to a brand new custom project
        res = self.client.post(
            f"/admin/gallery/edit/{item_id}",
            json={
                "project_id": "__new__",
                "new_project_title": "Brand New Neon Universe"
            }
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            created_proj = Project.query.filter_by(title="Brand New Neon Universe").first()
            self.assertIsNotNone(created_proj)
            self.assertEqual(created_proj.slug, "brand-new-neon-universe")

            updated_item = db.session.get(GalleryItem, item_id)
            self.assertEqual(updated_item.project_id, created_proj.id)
            self.assertEqual(updated_item.project.title, "Brand New Neon Universe")

    def test_admin_gallery_bulk_actions(self):
        self.login_admin()
        with self.app.app_context():
            items = GalleryItem.query.all()
            ids = [i.id for i in items]
            proj = Project.query.filter_by(title="PawShop Mobile").first()
            proj_id = proj.id

        # Bulk change category
        res = self.client.post(
            "/admin/gallery/bulk-action",
            json={
                "action": "change_category",
                "ids": ids,
                "new_category": "AI"
            }
        )
        self.assertEqual(res.status_code, 200)
        with self.app.app_context():
            for item in GalleryItem.query.filter(GalleryItem.id.in_(ids)).all():
                self.assertEqual(item.category, "AI")

        # Bulk change visibility
        res = self.client.post(
            "/admin/gallery/bulk-action",
            json={
                "action": "change_visibility",
                "ids": ids,
                "new_visibility": "published"
            }
        )
        self.assertEqual(res.status_code, 200)
        with self.app.app_context():
            for item in GalleryItem.query.filter(GalleryItem.id.in_(ids)).all():
                self.assertEqual(item.visibility, "published")

        # Bulk move to project
        res = self.client.post(
            "/admin/gallery/bulk-action",
            json={
                "action": "move_to_project",
                "ids": ids,
                "new_project_id": proj_id
            }
        )
        self.assertEqual(res.status_code, 200)
        with self.app.app_context():
            for item in GalleryItem.query.filter(GalleryItem.id.in_(ids)).all():
                self.assertEqual(item.project_id, proj_id)

        # Bulk delete
        res = self.client.post(
            "/admin/gallery/bulk-action",
            json={
                "action": "delete",
                "ids": [ids[0]]
            }
        )
        self.assertEqual(res.status_code, 200)
        with self.app.app_context():
            self.assertIsNone(GalleryItem.query.get(ids[0]))

    def test_public_security_visibility(self):
        # Public website should only show published items
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        # Ensure private/draft items are not publicly visible
        self.assertNotIn(b"Secret Neon Graphic Asset", res.data)

if __name__ == "__main__":
    unittest.main()

