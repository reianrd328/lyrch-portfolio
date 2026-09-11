from datetime import datetime
from . import db

class Skill(db.Model):
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default="IT Operations")  # IT Operations, Development, AI & Media
    level = db.Column(db.Integer, default=90)  # Percentage 0-100
    icon = db.Column(db.String(50), nullable=True)
    featured = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Skill {self.name}>"

