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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

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

    def __repr__(self):
        return f"<User {self.username}>"

