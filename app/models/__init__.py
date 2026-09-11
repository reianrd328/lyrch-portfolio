from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User
from .project import Project, ProjectImage
from .video import Video
from .gallery import GalleryItem
from .document import Document
from .skill import Skill
from .experience import Experience
from .category import Category
from .blog import BlogPost
from .activity import ActivityLog
from .settings import SiteSetting

__all__ = [
    "db",
    "User",
    "Project",
    "ProjectImage",
    "Video",
    "GalleryItem",
    "Document",
    "Skill",
    "Experience",
    "Category",
    "BlogPost",
    "ActivityLog",
    "SiteSetting",
]

