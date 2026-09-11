from . import db

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    scope = db.Column(db.String(30), default="project")  # project, video, gallery, document
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Category {self.name}>"

