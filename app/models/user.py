from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), default="LYRCH Admin")
    role = db.Column(db.String(20), default="admin")
    is_active_account = db.Column(db.Boolean, default=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("portfolio_profiles.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    profile = db.relationship("PortfolioProfile", backref=db.backref("user_accounts", lazy="dynamic"), foreign_keys=[profile_id])

    # Single-device active session tracking
    active_session_token = db.Column(db.String(64), nullable=True)
    active_session_device = db.Column(db.String(255), nullable=True)
    active_session_heartbeat = db.Column(db.DateTime, nullable=True)
    active_session_ip = db.Column(db.String(64), nullable=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_account

    @property
    def avatar_url(self) -> str:
        """Returns the avatar photo for this user, from linked profile or site settings."""
        if self.profile:
            return self.profile.avatar_url
        try:
            from app.models.settings import SiteSetting
            settings = SiteSetting.get_settings()
            return (settings.avatar_url if settings and settings.avatar_url else "/static/images/profile/avatar.jpg")
        except Exception:
            return "/static/images/profile/avatar.jpg"

    @avatar_url.setter
    def avatar_url(self, value: str):
        """Sets avatar url on linked profile or site settings."""
        if self.profile:
            data = self.profile.get_data()
            if "settings" not in data:
                data["settings"] = {}
            data["settings"]["avatar_url"] = value
            self.profile.set_data(data)
        try:
            from app.models.settings import SiteSetting
            settings = SiteSetting.get_settings()
            if settings:
                settings.avatar_url = value
        except Exception:
            pass

    def __repr__(self):
        return f"<User {self.username}>"

