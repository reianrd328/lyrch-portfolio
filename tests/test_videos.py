import io
import unittest
from app import create_app
from app.models import db, Video, User

class VideoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            u = User(username="admin", email="admin@lyrch.dev")
            u.set_password("adminpass")
            db.session.add(u)

            v1 = Video(
                title="AI Kung Fu Scene",
                slug="ai-kung-fu-scene",
                album="Kung Fu Chronicles",
                tools_used="Gemini, Video Edit",
                duration="0:10",
                featured=True,
                visibility="published"
            )
            v2 = Video(
                title="AI Kung Fu Finale",
                slug="ai-kung-fu-finale",
                album="Kung Fu Chronicles",
                tools_used="Gemini, Video Edit",
                duration="0:15",
                featured=False,
                visibility="published"
            )
            v3 = Video(
                title="Coffee Commercial Ad",
                slug="coffee-commercial-ad",
                album="Commercials 2026",
                tools_used="Gemini, Runway",
                duration="0:30",
                featured=True,
                visibility="published"
            )
            v4 = Video(
                title="Coffee Commercial Ad Standalone",
                slug="coffee-commercial-ad-standalone",
                album=None,
                tools_used="Gemini, Runway",
                duration="0:30",
                featured=False,
                visibility="published"
            )
            db.session.add_all([v1, v2, v3, v4])
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

    def test_video_studio_public_albums(self):
        response = self.client.get("/video-studio")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"AI CREATIVE VIDEO STUDIO", response.data)
        self.assertIn(b"Kung Fu Chronicles", response.data)
        self.assertIn(b"Commercials 2026", response.data)
        self.assertIn(b"AI Kung Fu Scene", response.data)
        self.assertIn(b"Coffee Commercial Ad", response.data)
        # Check album pill count
        self.assertIn(b"Kung Fu Chronicles (2)", response.data)
        self.assertIn(b"Commercials 2026 (1)", response.data)

    def test_admin_create_video_with_album(self):
        self.login_admin()
        res = self.client.post("/admin/videos/create", data={
            "title": "Cyberpunk Drone Chase",
            "album": "Sci-Fi Action",
            "category": "AI Creative",
            "tools_used": "Gemini, After Effects",
            "duration": "0:20",
            "aspect_ratio": "16:9",
            "visibility": "published"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Cyberpunk Drone Chase", res.data)
        self.assertIn(b"Sci-Fi Action", res.data)

        with self.app.app_context():
            v = Video.query.filter_by(title="Cyberpunk Drone Chase").first()
            self.assertIsNotNone(v)
            self.assertEqual(v.album, "Sci-Fi Action")

    def test_admin_edit_video_album(self):
        self.login_admin()
        with self.app.app_context():
            v = Video.query.filter_by(slug="coffee-commercial-ad").first()
            v_id = v.id

        res = self.client.post(f"/admin/videos/edit/{v_id}", data={
            "title": "Coffee Commercial Ad Extended",
            "album": "Premium Brand Series",
            "category": "Commercial",
            "tools_used": "Gemini, Premier Pro",
            "duration": "0:45",
            "aspect_ratio": "16:9",
            "visibility": "published"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"updated successfully", res.data)

        with self.app.app_context():
            updated = db.session.get(Video, v_id)
            self.assertEqual(updated.title, "Coffee Commercial Ad Extended")
            self.assertEqual(updated.album, "Premium Brand Series")

    def test_admin_filter_by_album(self):
        self.login_admin()
        res = self.client.get("/admin/videos/?album=Kung Fu Chronicles")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"AI Kung Fu Scene", res.data)
        self.assertIn(b"AI Kung Fu Finale", res.data)
        self.assertNotIn(b"Coffee Commercial Ad", res.data)

    def test_admin_create_and_edit_page_dropdown(self):
        self.login_admin()
        create_page = self.client.get("/admin/videos/create")
        self.assertEqual(create_page.status_code, 200)
        self.assertIn(b"id=\"albumSelect\"", create_page.data)
        self.assertIn(b"Kung Fu Chronicles", create_page.data)
        self.assertIn(b"Commercials 2026", create_page.data)
        self.assertIn(b"+ Create New Album...", create_page.data)

        # Test creating by selecting existing album from dropdown
        res_select = self.client.post("/admin/videos/create", data={
            "title": "Kung Fu Ep 3",
            "album_select": "Kung Fu Chronicles",
            "category": "AI Creative",
            "duration": "0:12"
        }, follow_redirects=True)
        self.assertEqual(res_select.status_code, 200)
        with self.app.app_context():
            v = Video.query.filter_by(title="Kung Fu Ep 3").first()
            self.assertIsNotNone(v)
            self.assertEqual(v.album, "Kung Fu Chronicles")

        # Test creating new album via __new__ and album_custom
        res_custom = self.client.post("/admin/videos/create", data={
            "title": "Mecha Titan Battle",
            "album_select": "__new__",
            "album_custom": "Mecha Cinematic Series",
            "category": "AI Creative",
            "duration": "0:18"
        }, follow_redirects=True)
        self.assertEqual(res_custom.status_code, 200)
        with self.app.app_context():
            v2 = Video.query.filter_by(title="Mecha Titan Battle").first()
            self.assertIsNotNone(v2)
            self.assertEqual(v2.album, "Mecha Cinematic Series")

    def test_admin_album_hub_and_inside_view(self):
        self.login_admin()
        # 1. Main AI Video Studio Production Manager Dashboard View
        hub_res = self.client.get("/admin/videos/")
        self.assertEqual(hub_res.status_code, 200)
        self.assertIn(b"AI VIDEO STUDIO", hub_res.data)
        self.assertIn(b"Production Manager", hub_res.data)
        self.assertIn(b"VIDEO LIBRARY", hub_res.data)
        self.assertIn(b"YOUR ALBUMS", hub_res.data)
        self.assertIn(b"+ CREATE ALBUM", hub_res.data)
        self.assertIn(b"Kung Fu Chronicles", hub_res.data)
        self.assertIn(b"Commercials 2026", hub_res.data)
        self.assertIn(b"STANDALONE VIDEOS", hub_res.data)
        self.assertIn(b"Coffee Commercial Ad Standalone", hub_res.data)

        # 2. Inside Album View (Click into Kung Fu Chronicles)
        inside_res = self.client.get("/admin/videos/?album=Kung Fu Chronicles")
        self.assertEqual(inside_res.status_code, 200)
        self.assertIn(b"All Albums", inside_res.data)
        self.assertIn(b"Kung Fu Chronicles", inside_res.data)
        self.assertIn(b"AI Kung Fu Scene", inside_res.data)
        self.assertIn(b"AI Kung Fu Finale", inside_res.data)
        self.assertNotIn(b"Coffee Commercial Ad Standalone", inside_res.data)

        # 3. Filter Tabs (e.g. albums tab, standalone tab)
        tab_albums = self.client.get("/admin/videos/?tab=albums")
        self.assertEqual(tab_albums.status_code, 200)
        self.assertIn(b"YOUR ALBUMS", tab_albums.data)
        self.assertNotIn(b"STANDALONE VIDEOS", tab_albums.data)

        tab_standalone = self.client.get("/admin/videos/?tab=standalone")
        self.assertEqual(tab_standalone.status_code, 200)
        self.assertIn(b"STANDALONE VIDEOS", tab_standalone.data)
        self.assertNotIn(b"YOUR ALBUMS", tab_standalone.data)

    def test_admin_batch_video_upload(self):
        self.login_admin()

        # 1. Batch upload multiple videos into an album with custom title
        vid1 = (io.BytesIO(b"fake mp4 video bytes 1"), "cyber_scene_a.mp4")
        vid2 = (io.BytesIO(b"fake mp4 video bytes 2"), "cyber_scene_b.mp4")

        res = self.client.post("/admin/videos/create", data={
            "title": "Neon Chase",
            "album_select": "Kung Fu Chronicles",
            "category": "AI Creative",
            "tools_used": "Gemini Video, Runway Gen-3",
            "duration": "0:15",
            "aspect_ratio": "9:16",
            "visibility": "published",
            "videos": [vid1, vid2]
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Kung Fu Chronicles", res.data)
        self.assertIn(b"Neon Chase - Part 1", res.data)
        self.assertIn(b"Neon Chase - Part 2", res.data)

        with self.app.app_context():
            v1 = Video.query.filter_by(title="Neon Chase - Part 1").first()
            v2 = Video.query.filter_by(title="Neon Chase - Part 2").first()
            self.assertIsNotNone(v1)
            self.assertIsNotNone(v2)
            self.assertEqual(v1.album, "Kung Fu Chronicles")
            self.assertEqual(v2.album, "Kung Fu Chronicles")
            self.assertEqual(v1.aspect_ratio, "9:16")

        # 2. Batch upload with blank title into a new album (auto-deriving filenames)
        vidA = (io.BytesIO(b"fake webm bytes A"), "epic_boss_fight.mp4")
        vidB = (io.BytesIO(b"fake webm bytes B"), "victory_celebration.mp4")

        res_new_album = self.client.post("/admin/videos/create", data={
            "title": "",
            "album_select": "__new__",
            "album_custom": "Epic Boss Series",
            "category": "Commercial",
            "videos": [vidA, vidB]
        }, follow_redirects=True)

        self.assertEqual(res_new_album.status_code, 200)
        self.assertIn(b"Epic Boss Series", res_new_album.data)
        self.assertIn(b"Epic Boss Fight", res_new_album.data)
        self.assertIn(b"Victory Celebration", res_new_album.data)

        with self.app.app_context():
            va = Video.query.filter_by(title="Epic Boss Fight").first()
            vb = Video.query.filter_by(title="Victory Celebration").first()
            self.assertIsNotNone(va)
            self.assertIsNotNone(vb)
            self.assertEqual(va.album, "Epic Boss Series")
            self.assertEqual(vb.album, "Epic Boss Series")

    def test_video_profile_scoping_admin(self):
        from app.models import PortfolioProfile
        self.login_admin()

        with self.app.app_context():
            prof1 = PortfolioProfile(name="Richard Master", slug="richard-master", is_active=True, is_published=True, data_json="{}")
            prof2 = PortfolioProfile(name="Tobias Client", slug="tobias-client", is_active=False, is_published=True, data_json="{}")
            db.session.add_all([prof1, prof2])
            db.session.commit()
            p1_id = prof1.id
            p2_id = prof2.id

        # Upload video for Profile 1
        res1 = self.client.post("/admin/videos/create", data={
            "title": "Master Video Reel",
            "album_select": "Master Series",
            "category": "AI Creative",
            "profile_id": str(p1_id),
            "visibility": "published"
        }, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        # Upload video for Profile 2 (Tobias)
        res2 = self.client.post("/admin/videos/create", data={
            "title": "Tobias Special Video",
            "album_select": "Tobias Album",
            "category": "AI Creative",
            "profile_id": str(p2_id),
            "visibility": "published"
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        # Admin views Profile 2 scope (Hub view shows albums and standalone)
        res_scope2 = self.client.get(f"/admin/videos/?profile_id={p2_id}")
        self.assertEqual(res_scope2.status_code, 200)
        self.assertIn(b"Tobias Album", res_scope2.data)
        self.assertNotIn(b"Master Series", res_scope2.data)
        self.assertNotIn(b"Master Video Reel", res_scope2.data)

        # Inside Album view for Profile 2 shows the individual video
        res_inside_tobias = self.client.get(f"/admin/videos/?album=Tobias+Album&profile_id={p2_id}")
        self.assertEqual(res_inside_tobias.status_code, 200)
        self.assertIn(b"Tobias Special Video", res_inside_tobias.data)
        self.assertNotIn(b"Master Video Reel", res_inside_tobias.data)

        # Admin views Profile 1 scope
        res_scope1 = self.client.get(f"/admin/videos/?profile_id={p1_id}")
        self.assertEqual(res_scope1.status_code, 200)
        self.assertIn(b"Master Series", res_scope1.data)
        self.assertNotIn(b"Tobias Album", res_scope1.data)

        # Public /p/tobias-client/video-studio renders Tobias's video
        res_pub_tobias = self.client.get("/p/tobias-client/video-studio")
        self.assertEqual(res_pub_tobias.status_code, 200)
        self.assertIn(b"Tobias Special Video", res_pub_tobias.data)
        self.assertIn(b"Tobias Album", res_pub_tobias.data)
        self.assertNotIn(b"Master Video Reel", res_pub_tobias.data)

        # Public root /video-studio renders active profile items
        res_pub_root = self.client.get("/video-studio")
        self.assertEqual(res_pub_root.status_code, 200)
        self.assertIn(b"Master Video Reel", res_pub_root.data)
        self.assertNotIn(b"Tobias Special Video", res_pub_root.data)

    def test_video_profile_user_permissions(self):
        from app.models import PortfolioProfile
        with self.app.app_context():
            prof1 = PortfolioProfile(name="Richard Master", slug="richard-master", is_active=True, is_published=True, data_json="{}")
            prof2 = PortfolioProfile(name="Tobias Client", slug="tobias-client", is_active=False, is_published=True, data_json="{}")
            db.session.add_all([prof1, prof2])
            db.session.commit()

            # Create video for prof1
            v_master = Video(title="Richard Exclusive", slug="richard-exclusive", profile_id=prof1.id, visibility="published")
            db.session.add(v_master)

            # Create profile user for prof2 (Tobias)
            user_tobias = User(username="tobias_tester", email="tobias@test.dev", role="profile_user", profile_id=prof2.id)
            user_tobias.set_password("tobiaspass")
            db.session.add(user_tobias)
            db.session.commit()
            v_master_id = v_master.id
            p2_id = prof2.id

        # Log in as profile user Tobias
        self.client.post("/auth/login", data={
            "username": "tobias_tester",
            "password": "tobiaspass"
        }, follow_redirects=True)

        # Tobias accesses /admin/videos/
        res_index = self.client.get("/admin/videos/")
        self.assertEqual(res_index.status_code, 200)
        # Should NOT see Richard Exclusive
        self.assertNotIn(b"Richard Exclusive", res_index.data)

        # Tobias uploads a new video
        res_upload = self.client.post("/admin/videos/create", data={
            "title": "Tobias Personal Story",
            "category": "AI Creative",
            "duration": "0:10",
            "visibility": "published"
        }, follow_redirects=True)
        self.assertEqual(res_upload.status_code, 200)

        with self.app.app_context():
            v_new = Video.query.filter_by(title="Tobias Personal Story").first()
            self.assertIsNotNone(v_new)
            # Must be strictly assigned to Tobias's profile
            self.assertEqual(v_new.profile_id, p2_id)

            # Check profile data_json was automatically synced
            prof2_check = PortfolioProfile.query.get(p2_id)
            videos_json = prof2_check.get_data().get("videos", [])
            self.assertTrue(any(v.get("title") == "Tobias Personal Story" for v in videos_json))

        # Tobias attempts to edit or delete Richard Exclusive (must get 403 Forbidden)
        res_edit_forbidden = self.client.post(f"/admin/videos/edit/{v_master_id}", data={
            "title": "Hacked Title"
        })
        self.assertEqual(res_edit_forbidden.status_code, 403)

        res_delete_forbidden = self.client.post(f"/admin/videos/delete/{v_master_id}")
        self.assertEqual(res_delete_forbidden.status_code, 403)

    def test_safe_shared_thumbnail_deletion(self):
        import os
        from app.models import Video

        self.login_admin()
        upload_folder = self.app.config["UPLOAD_FOLDER"]
        video_dir = os.path.join(upload_folder, "videos")
        os.makedirs(video_dir, exist_ok=True)
        test_thumb_file = os.path.join(video_dir, "test_shared_thumb_safe.png")
        with open(test_thumb_file, "wb") as f:
            f.write(b"fake image data")

        shared_url = "/uploads/videos/test_shared_thumb_safe.png"

        with self.app.app_context():
            v_ep1 = Video(title="Series Ep 1", slug="series-ep-1", album="My Series", thumbnail_url=shared_url, visibility="published")
            v_ep2 = Video(title="Series Ep 2", slug="series-ep-2", album="My Series", thumbnail_url=shared_url, visibility="published")
            db.session.add_all([v_ep1, v_ep2])
            db.session.commit()
            ep1_id = v_ep1.id
            ep2_id = v_ep2.id

        # Delete Ep 1
        res = self.client.post(f"/admin/videos/delete/{ep1_id}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # File must STILL exist because Ep 2 is still using it!
        self.assertTrue(os.path.exists(test_thumb_file), "Shared thumbnail file must NOT be deleted while Ep 2 references it")

        # Now delete Ep 2 (last remaining reference)
        res2 = self.client.post(f"/admin/videos/delete/{ep2_id}", follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        # Now the file should be deleted
        self.assertFalse(os.path.exists(test_thumb_file), "Thumbnail file should be deleted when the last video referencing it is deleted")

if __name__ == "__main__":
    unittest.main()

