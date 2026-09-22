from datetime import datetime
import json
from . import db

class PortfolioProfile(db.Model):
    __tablename__ = "portfolio_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    client_name = db.Column(db.String(120), default="")
    description = db.Column(db.Text, default="")
    theme_preset = db.Column(db.String(50), default="cyber")
    is_active = db.Column(db.Boolean, default=False, index=True)
    is_published = db.Column(db.Boolean, default=True, index=True)  # True = LIVE & ONLINE, False = DRAFT & OFFLINE
    data_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_data(self) -> dict:
        """Parses and returns the snapshot JSON payload."""
        try:
            return json.loads(self.data_json) if self.data_json else {}
        except Exception:
            return {}

    def set_data(self, data_dict: dict):
        """Serializes dictionary to data_json string."""
        self.data_json = json.dumps(data_dict, indent=2, default=str)

    @property
    def project_count(self) -> int:
        data = self.get_data()
        return len(data.get("projects", []))

    @property
    def skill_count(self) -> int:
        data = self.get_data()
        return len(data.get("skills", []))

    @property
    def user_account(self):
        """Returns the primary user account linked to this profile."""
        from app.models.user import User
        return User.query.filter_by(profile_id=self.id).first()

    @property
    def avatar_url(self) -> str:
        """Returns the profile picture URL configured in snapshot settings or default."""
        data = self.get_data()
        return data.get("settings", {}).get("avatar_url") or "/static/images/profile/avatar.jpg"

    def __repr__(self):
        return f"<PortfolioProfile {self.name} (slug={self.slug}, active={self.is_active})>"

