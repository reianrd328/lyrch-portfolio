import io
import unittest
from app import create_app
from app.models import db, GalleryItem, Project, User, SiteSetting, PortfolioProfile
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

    def test_gallery_category_customization(self):
        self.login_admin()

        # Update categories via JSON endpoint
        custom_cats = "Photography, 3D Architecture, Motion Design, Branding, Other"
        res = self.client.post(
            "/admin/gallery/categories/update",
            json={"categories": custom_cats}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("Photography", data["categories"])
        self.assertIn("3D Architecture", data["categories"])

        with self.app.app_context():
            settings = SiteSetting.get_settings()
            self.assertEqual(settings.gallery_categories, "Photography, 3D Architecture, Motion Design, Branding, Other")

        # Verify the admin gallery index displays the new categories
        index_res = self.client.get("/admin/gallery/")
        self.assertEqual(index_res.status_code, 200)
        self.assertIn(b"Photography", index_res.data)
        self.assertIn(b"3D Architecture", index_res.data)
        self.assertIn(b"Edit Categories", index_res.data)

    def test_gallery_on_the_fly_custom_category(self):
        self.login_admin()
        with self.app.app_context():
            item = GalleryItem.query.filter_by(title="HUD Analytics Interface").first()
            item_id = item.id

        # Edit item and supply __custom__ category with custom_category="Generative Cyber Art"
        res = self.client.post(
            f"/admin/gallery/edit/{item_id}",
            json={
                "title": "HUD Analytics Interface",
                "category": "__custom__",
                "custom_category": "Generative Cyber Art"
            }
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            updated = db.session.get(GalleryItem, item_id)
            self.assertEqual(updated.category, "Generative Cyber Art")

            # Verify it was also appended to configured SiteSetting categories
            settings = SiteSetting.get_settings()
            self.assertIn("Generative Cyber Art", settings.gallery_categories)

    def test_gallery_batch_multi_upload(self):
        self.login_admin()
        with self.app.app_context():
            p = Project.query.filter_by(title="Cyberpunk Dashboard").first()
            p_id = p.id

        # 1. Batch upload with custom title
        img1 = (io.BytesIO(b"fake image data 1"), "screen_one.png")
        img2 = (io.BytesIO(b"fake image data 2"), "screen_two.png")
        img3 = (io.BytesIO(b"fake image data 3"), "screen_three.png")

        res = self.client.post("/admin/gallery/create", data={
            "title": "Batch Showcase",
            "category": "UI / UX",
            "project_id": str(p_id),
            "description": "Multi-upload test",
            "tags": "multi, batch",
            "visibility": "published",
            "images": [img1, img2, img3]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            item1 = GalleryItem.query.filter_by(title="Batch Showcase (1)").first()
            item2 = GalleryItem.query.filter_by(title="Batch Showcase (2)").first()
            item3 = GalleryItem.query.filter_by(title="Batch Showcase (3)").first()
            self.assertIsNotNone(item1)
            self.assertIsNotNone(item2)
            self.assertIsNotNone(item3)
            self.assertEqual(item1.project_id, p_id)
            self.assertEqual(item2.project_id, p_id)
            self.assertEqual(item3.category, "UI / UX")

        # 2. Batch upload with blank title (auto-deriving filename)
        imgA = (io.BytesIO(b"fake image A"), "mobile_login_flow.png")
        imgB = (io.BytesIO(b"fake image B"), "checkout_success_hud.png")

        res_blank = self.client.post("/admin/gallery/create", data={
            "title": "",
            "category": "Screenshots",
            "visibility": "published",
            "images": [imgA, imgB]
        }, follow_redirects=True)
        self.assertEqual(res_blank.status_code, 200)

        with self.app.app_context():
            itemA = GalleryItem.query.filter_by(title="Mobile Login Flow").first()
            itemB = GalleryItem.query.filter_by(title="Checkout Success Hud").first()
            self.assertIsNotNone(itemA)
            self.assertIsNotNone(itemB)
            self.assertEqual(itemA.category, "Screenshots")

    def test_gallery_project_albums_view(self):
        self.login_admin()
        with self.app.app_context():
            p1 = Project.query.filter_by(title="Cyberpunk Dashboard").first()
            p1_id = p1.id
            p2 = Project.query.filter_by(title="PawShop Mobile").first()
            p2_id = p2.id

        # 1. Visiting category 'Projects' defaults to Project Albums view
        res = self.client.get("/admin/gallery/?cat=Projects")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"YOUR PROJECT ALBUMS", res.data)
        self.assertIn(b"PROJECT ALBUM", res.data)
        self.assertIn(b"Cyberpunk Dashboard", res.data)
        self.assertIn(b"PawShop Mobile", res.data)
        self.assertIn(b"OPEN ALBUM", res.data)
        self.assertIn(b"+ NEW PROJECT ASSETS", res.data)
        self.assertIn(b"Flat Grid", res.data)

        # 2. Visiting with view=flat shows loose assets grid
        res_flat = self.client.get("/admin/gallery/?cat=Projects&view=flat")
        self.assertEqual(res_flat.status_code, 200)
        self.assertIn(b"HUD Analytics Interface", res_flat.data)
        self.assertIn(b"PawShop Checkout Flow", res_flat.data)

        # 3. Drilling down into a specific project album (?project_id=...)
        res_drilldown = self.client.get(f"/admin/gallery/?project_id={p1_id}")
        self.assertEqual(res_drilldown.status_code, 200)
        self.assertIn(b"CURRENT PROJECT ALBUM", res_drilldown.data)
        self.assertIn(b"Cyberpunk Dashboard", res_drilldown.data)
        self.assertIn(b"All Project Albums", res_drilldown.data)
        self.assertIn(b"+ Upload to This Project", res_drilldown.data)
        self.assertIn(b"HUD Analytics Interface", res_drilldown.data)
        # PawShop asset should NOT be in this project album
        self.assertNotIn(b"PawShop Checkout Flow", res_drilldown.data)

    def test_gallery_profile_scoping_admin(self):
        self.login_admin()
        with self.app.app_context():
            # Setup Profile A (active root) and Profile B (secondary)
            prof_a = PortfolioProfile(name="Master Drop Farmd", slug="master-drop", is_active=True, is_published=True)
            prof_b = PortfolioProfile(name="Client John Doe", slug="john-doe", is_active=False, is_published=True)
            db.session.add_all([prof_a, prof_b])
            db.session.commit()
            prof_a_id = prof_a.id
            prof_b_id = prof_b.id

        # Upload image for Profile A
        img_a = (io.BytesIO(b"fake data A"), "image_a.png")
        res_a = self.client.post("/admin/gallery/create", data={
            "title": "Master Brand Asset",
            "category": "Branding",
            "profile_id": str(prof_a_id),
            "visibility": "published",
            "images": [img_a]
        }, follow_redirects=True)
        self.assertEqual(res_a.status_code, 200)

        # Upload image for Profile B
        img_b = (io.BytesIO(b"fake data B"), "image_b.png")
        res_b = self.client.post("/admin/gallery/create", data={
            "title": "Client Secret Visual",
            "category": "UI / UX",
            "profile_id": str(prof_b_id),
            "visibility": "published",
            "images": [img_b]
        }, follow_redirects=True)
        self.assertEqual(res_b.status_code, 200)

        # Admin views Profile B gallery scope
        res_scoped_b = self.client.get(f"/admin/gallery/?profile_id={prof_b_id}")
        self.assertEqual(res_scoped_b.status_code, 200)
        self.assertIn(b"Client Secret Visual", res_scoped_b.data)
        self.assertNotIn(b"Master Brand Asset", res_scoped_b.data)

        # Admin views Profile A gallery scope
        res_scoped_a = self.client.get(f"/admin/gallery/?profile_id={prof_a_id}")
        self.assertEqual(res_scoped_a.status_code, 200)
        self.assertIn(b"Master Brand Asset", res_scoped_a.data)
        self.assertNotIn(b"Client Secret Visual", res_scoped_a.data)

        # Public /p/john-doe/gallery only renders Client Secret Visual
        res_pub_b = self.client.get("/p/john-doe/gallery")
        self.assertEqual(res_pub_b.status_code, 200)
        self.assertIn(b"Client Secret Visual", res_pub_b.data)
        self.assertNotIn(b"Master Brand Asset", res_pub_b.data)

        # Public /gallery (root) only renders active profile items
        res_pub_root = self.client.get("/gallery")
        self.assertEqual(res_pub_root.status_code, 200)
        self.assertIn(b"Master Brand Asset", res_pub_root.data)
        self.assertNotIn(b"Client Secret Visual", res_pub_root.data)

    def test_gallery_profile_user_permissions(self):
        with self.app.app_context():
            prof_c = PortfolioProfile(name="Profile User Test", slug="prof-user-test", is_active=False, is_published=True)
            db.session.add(prof_c)
            db.session.commit()
            prof_c_id = prof_c.id

            # Create profile user account
            pu = User(username="client_user", email="client@test.local", role="profile_user", profile_id=prof_c_id)
            pu.set_password("clientpass")
            db.session.add(pu)

            # Create asset for another profile
            other_item = GalleryItem(
                title="Other Profile Asset",
                category="UI / UX",
                image_url="/static/images/placeholder.jpg",
                visibility="published"
            )
            # Create asset for this profile user
            user_item = GalleryItem(
                title="My Own Profile Asset",
                category="UI / UX",
                profile_id=prof_c_id,
                image_url="/static/images/placeholder.jpg",
                visibility="published"
            )
            db.session.add_all([other_item, user_item])
            db.session.commit()
            other_id = other_item.id
            user_id = user_item.id

        # Login as profile user
        self.client.post("/auth/login", data={"username": "client_user", "password": "clientpass"}, follow_redirects=True)

        # Admin gallery is automatically scoped to their profile
        res = self.client.get("/admin/gallery/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"My Own Profile Asset", res.data)
        self.assertNotIn(b"Other Profile Asset", res.data)

        # Trying to api_item or delete other profile's asset returns 403 Forbidden
        res_api_other = self.client.get(f"/admin/gallery/api/item/{other_id}")
        self.assertEqual(res_api_other.status_code, 403)

        res_del_other = self.client.post(f"/admin/gallery/delete/{other_id}")
        self.assertEqual(res_del_other.status_code, 403)

        # Can delete own asset
        res_del_own = self.client.post(f"/admin/gallery/delete/{user_id}", follow_redirects=True)
        self.assertEqual(res_del_own.status_code, 200)
        with self.app.app_context():
            deleted_check = db.session.get(GalleryItem, user_id)
            self.assertIsNone(deleted_check)

if __name__ == "__main__":
    unittest.main()


