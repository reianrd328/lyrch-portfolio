from datetime import datetime
from . import db

class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    activity_type = db.Column(db.String(50), default="project") # project, video, network, git, ai
    time_label = db.Column(db.String(50), default="Just now")    # e.g. "2 hours ago"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ActivityLog {self.title}>"

