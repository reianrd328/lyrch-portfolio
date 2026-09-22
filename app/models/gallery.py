from datetime import datetime
from . import db

class GalleryItem(db.Model):
    __tablename__ = "gallery"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), default="UI / UX")
    image_url = db.Column(db.String(255), nullable=False)
    thumbnail_url = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    featured = db.Column(db.Boolean, default=False)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Project Relationship & Categorization
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    project = db.relationship("Project", backref=db.backref("gallery_items", lazy="dynamic"))

    # Portfolio Profile Scoping
    profile_id = db.Column(db.Integer, db.ForeignKey("portfolio_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    profile = db.relationship("PortfolioProfile", backref=db.backref("gallery_items", lazy="dynamic"), foreign_keys=[profile_id])

    # Status: 'published', 'draft', 'private'
    visibility = db.Column(db.String(20), default="published", index=True)
    tags = db.Column(db.String(255), nullable=True)
    file_size_bytes = db.Column(db.Integer, default=0, nullable=True)

    @property
    def tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def file_size_formatted(self):
        from app.services.storage_service import format_bytes
        return format_bytes(self.file_size_bytes or 0)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "image_url": self.image_url,
            "thumbnail_url": self.thumbnail_url or self.image_url,
            "description": self.description or "",
            "featured": self.featured,
            "order_index": self.order_index,
            "created_at": self.created_at.strftime("%b %d, %Y") if self.created_at else "",
            "project_id": self.project_id,
            "project_title": self.project.title if self.project else None,
            "profile_id": self.profile_id,
            "profile_name": self.profile.name if self.profile else None,
            "visibility": self.visibility or "published",
            "tags": self.tags or "",
            "tags_list": self.tags_list,
            "file_size_bytes": self.file_size_bytes or 0,
            "file_size_formatted": self.file_size_formatted
        }

    def __repr__(self):
        return f"<GalleryItem {self.title}>"

