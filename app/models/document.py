from datetime import datetime
from . import db

class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), default="PDF")
    file_size = db.Column(db.Integer, default=0)  # in bytes
    category = db.Column(db.String(60), default="Documentation")
    description = db.Column(db.Text, nullable=True)
    allow_download = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Portfolio Profile Scoping
    profile_id = db.Column(db.Integer, db.ForeignKey("portfolio_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    profile = db.relationship("PortfolioProfile", backref=db.backref("documents", lazy="dynamic"), foreign_keys=[profile_id])

    @property
    def formatted_size(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "formatted_size": self.formatted_size,
            "category": self.category,
            "description": self.description or "",
            "allow_download": self.allow_download,
            "is_public": self.is_public,
            "profile_id": self.profile_id,
            "profile_name": self.profile.name if self.profile else None,
            "created_at": self.created_at.strftime("%b %d, %Y") if self.created_at else ""
        }

    def __repr__(self):
        return f"<Document {self.title}>"


