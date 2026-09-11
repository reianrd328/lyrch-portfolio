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

    def __repr__(self):
        return f"<Video {self.title}>"

