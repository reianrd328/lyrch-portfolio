from datetime import datetime
import json
from . import db

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    subtitle = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(60), default="Software Project")
    status_badge = db.Column(db.String(30), default="Live")  # Live, Beta, Demo, In Progress
    featured = db.Column(db.Boolean, default=False, index=True)
    order_index = db.Column(db.Integer, default=0)
    
    # Descriptions
    short_description = db.Column(db.Text, nullable=True)
    full_description = db.Column(db.Text, nullable=True)
    
    # Case Study Details
    problem = db.Column(db.Text, nullable=True)
    solution = db.Column(db.Text, nullable=True)
    challenges = db.Column(db.Text, nullable=True)
    results = db.Column(db.Text, nullable=True)
    
    # Tags and lists stored as comma or json
    technologies = db.Column(db.String(255), default="")  # "Python, Flask, MySQL"
    key_features = db.Column(db.Text, default="")         # JSON or newline-separated
    
    # Media & Links
    thumbnail_url = db.Column(db.String(255), nullable=True)
    banner_url = db.Column(db.String(255), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    demo_url = db.Column(db.String(255), nullable=True)
    documentation_url = db.Column(db.String(255), nullable=True)
    
    # Visibility: 'published', 'draft', 'private'
    visibility = db.Column(db.String(20), default="published", index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship("ProjectImage", backref="project", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def tech_list(self):
        if not self.technologies:
            return []
        return [t.strip() for t in self.technologies.split(",") if t.strip()]

    @property
    def features_list(self):
        if not self.key_features:
            return []
        try:
            return json.loads(self.key_features)
        except Exception:
            return [f.strip() for f in self.key_features.split("\n") if f.strip()]

    def __repr__(self):
        return f"<Project {self.title}>"


class ProjectImage(db.Model):
    __tablename__ = "project_images"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255), nullable=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

