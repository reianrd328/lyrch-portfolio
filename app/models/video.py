from datetime import datetime
from . import db

class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(255), nullable=True)
    thumbnail_url = db.Column(db.String(255), nullable=True)
    album = db.Column(db.String(100), nullable=True, index=True)  # Album / Series / Collection name (e.g. "Kung Fu Action", "Product Commercials")
    category = db.Column(db.String(50), default="AI Creative")  # Commercial, Reel, TikTok, Experiment
    tools_used = db.Column(db.String(255), default="Gemini, Video Editing")
    platforms = db.Column(db.String(255), default="Facebook Reels, TikTok")
    
    duration = db.Column(db.String(20), default="00:10")  # e.g. 0:10
    aspect_ratio = db.Column(db.String(20), default="9:16")
    
    # Process & Prompt Documentation
    prompt_text = db.Column(db.Text, nullable=True)
    workflow_notes = db.Column(db.Text, nullable=True)
    
    featured = db.Column(db.Boolean, default=False, index=True)
    visibility = db.Column(db.String(20), default="published", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Portfolio Profile Scoping
    profile_id = db.Column(db.Integer, db.ForeignKey("portfolio_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    profile = db.relationship("PortfolioProfile", backref=db.backref("videos", lazy="dynamic"), foreign_keys=[profile_id])

    @property
    def tools_list(self):
        if not self.tools_used:
            return []
        return [t.strip() for t in self.tools_used.split(",") if t.strip()]

    @property
    def platforms_list(self):
        if not self.platforms:
            return []
        return [p.strip() for p in self.platforms.split(",") if p.strip()]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "description": self.description or "",
            "video_url": self.video_url or "",
            "thumbnail_url": self.thumbnail_url or "",
            "album": self.album or "",
            "category": self.category or "AI Creative",
            "tools_used": self.tools_used or "",
            "tools_list": self.tools_list,
            "platforms": self.platforms or "",
            "platforms_list": self.platforms_list,
            "duration": self.duration or "00:10",
            "aspect_ratio": self.aspect_ratio or "9:16",
            "prompt_text": self.prompt_text or "",
            "workflow_notes": self.workflow_notes or "",
            "featured": self.featured,
            "visibility": self.visibility or "published",
            "profile_id": self.profile_id,
            "profile_name": self.profile.name if self.profile else None,
            "created_at": self.created_at.strftime("%b %d, %Y") if self.created_at else ""
        }

    def __repr__(self):
        return f"<Video {self.title}>"


