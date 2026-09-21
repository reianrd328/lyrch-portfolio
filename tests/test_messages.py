import unittest
from unittest.mock import patch
from app import create_app
from app.models import db, User, SiteSetting, ContactMessage, ActivityLog, PortfolioProfile

class ContactMessagesTestCase(unittest.TestCase):
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
            settings.contact_email = "target@example.com"
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

    @patch("app.routes.public.send_contact_message_email")
    def test_contact_form_submission_success(self, mock_send_email):
        """Test public contact form saves to ContactMessage and calls email dispatch."""
        response = self.client.post("/contact", data={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "message": "Hello! I am interested in collaborating with you."
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Signal received! Your transmission has reached the Command Center.", response.data)

        # Verify DB entry
        with self.app.app_context():
            msg = ContactMessage.query.first()
            self.assertIsNotNone(msg)
            self.assertEqual(msg.name, "Jane Doe")
            self.assertEqual(msg.email, "jane@example.com")
            self.assertEqual(msg.message, "Hello! I am interested in collaborating with you.")
            self.assertFalse(msg.is_read)

            # Verify ActivityLog
            log = ActivityLog.query.filter(ActivityLog.title.like("%Jane Doe%")).first()
            self.assertIsNotNone(log)

        # Verify email dispatch attempted
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args.kwargs
        self.assertEqual(call_kwargs["sender_name"], "Jane Doe")
        self.assertEqual(call_kwargs["sender_email"], "jane@example.com")
        self.assertEqual(call_kwargs["recipient_email"], "target@example.com")

    def test_admin_messages_requires_auth(self):
        """Test anonymous access to /admin/messages redirects to login."""
        response = self.client.get("/admin/messages")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_admin_messages_inbox_view_and_filtering(self):
        """Test viewing messages, unread badge, and filter/search query parameters."""
        # Seed test messages
        with self.app.app_context():
            m1 = ContactMessage(name="Alice Tech", email="alice@corp.com", message="Inquiry about cloud migration.", is_read=False)
            m2 = ContactMessage(name="Bob Designer", email="bob@creative.io", message="Love your cyberpunk styling!", is_read=True)
            db.session.add_all([m1, m2])
            db.session.commit()

        self.login_admin()

        # 1. View all
        res_all = self.client.get("/admin/messages")
        self.assertEqual(res_all.status_code, 200)
        self.assertIn(b"Alice Tech", res_all.data)
        self.assertIn(b"Bob Designer", res_all.data)
        self.assertIn(b"TRANSMISSIONS INBOX", res_all.data)

        # 2. Filter unread
        res_unread = self.client.get("/admin/messages?filter=unread")
        self.assertEqual(res_unread.status_code, 200)
        self.assertIn(b"Alice Tech", res_unread.data)
        self.assertNotIn(b"Bob Designer", res_unread.data)

        # 3. Filter read
        res_read = self.client.get("/admin/messages?filter=read")
        self.assertEqual(res_read.status_code, 200)
        self.assertNotIn(b"Alice Tech", res_read.data)
        self.assertIn(b"Bob Designer", res_read.data)

        # 4. Search query
        res_search = self.client.get("/admin/messages?q=migration")
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b"Alice Tech", res_search.data)
        self.assertNotIn(b"Bob Designer", res_search.data)

    def test_toggle_message_read(self):
        """Test toggling message is_read status."""
        with self.app.app_context():
            msg = ContactMessage(name="Charlie", email="charlie@web.com", message="Ping test.", is_read=False)
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

        self.login_admin()

        # Toggle to read
        res1 = self.client.post(f"/admin/messages/{msg_id}/toggle-read", follow_redirects=True)
        self.assertEqual(res1.status_code, 200)
        with self.app.app_context():
            m = ContactMessage.query.get(msg_id)
            self.assertTrue(m.is_read)

        # Toggle back to unread
        res2 = self.client.post(f"/admin/messages/{msg_id}/toggle-read", follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        with self.app.app_context():
            m = ContactMessage.query.get(msg_id)
            self.assertFalse(m.is_read)

    def test_delete_message(self):
        """Test deleting a message."""
        with self.app.app_context():
            msg = ContactMessage(name="Spam Bot", email="bot@spam.com", message="Buy crypto now.", is_read=True)
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

        self.login_admin()

        res = self.client.post(f"/admin/messages/{msg_id}/delete", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        with self.app.app_context():
            m = ContactMessage.query.get(msg_id)
            self.assertIsNone(m)

    def test_dashboard_displays_transmissions(self):
        """Test admin dashboard displays TRANSMISSIONS metric and recent incoming transmissions."""
        with self.app.app_context():
            msg = ContactMessage(name="Eva Recruiter", email="eva@talent.com", message="Great portfolio!", is_read=False)
            db.session.add(msg)
            db.session.commit()

        self.login_admin()
        res = self.client.get("/admin/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"TRANSMISSIONS", res.data)
        self.assertIn(b"RECENT INCOMING TRANSMISSIONS", res.data)
        self.assertIn(b"Eva Recruiter", res.data)

