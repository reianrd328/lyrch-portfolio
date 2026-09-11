from datetime import datetime
from . import db

class Experience(db.Model):
    __tablename__ = "experiences"

    id = db.Column(db.Integer, primary_key=True)
    role_title = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(100), default="Philippines")
    period = db.Column(db.String(60), nullable=False)  # e.g., 2008 - Present
    description = db.Column(db.Text, nullable=True)
    highlights = db.Column(db.Text, nullable=True)     # Newline-separated accomplishments
    order_index = db.Column(db.Integer, default=0)

    @property
    def highlights_list(self):
        if not self.highlights:
            return []
        return [h.strip() for h in self.highlights.split("\n") if h.strip()]

    def __repr__(self):
        return f"<Experience {self.role_title} at {self.company}>"

