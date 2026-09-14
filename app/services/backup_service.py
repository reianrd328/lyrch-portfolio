import json
from datetime import datetime
from app.models import (
    db, User, Project, ProjectImage, Category, Video, GalleryItem, Document,
    Skill, Experience, BlogPost, ActivityLog, SiteSetting
)

def serialize_model_instance(instance) -> dict:
    """Converts a SQLAlchemy model instance into a JSON-serializable dictionary."""
    data = {}
    for col in instance.__table__.columns:
        val = getattr(instance, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        data[col.name] = val
    return data

def export_database_to_dict() -> dict:
    """
    Serializes all tables in the application database into a structured dictionary.
    Works identically across SQLite, MySQL, and TiDB Cloud.
    """
    backup_data = {
        "metadata": {
            "version": "1.0",
            "app": "LYRCH Digital Command Center",
            "generated_at": datetime.utcnow().isoformat(),
        },
        "tables": {
            "users": [serialize_model_instance(u) for u in User.query.all()],
            "site_settings": [serialize_model_instance(s) for s in SiteSetting.query.all()],
            "categories": [serialize_model_instance(c) for c in Category.query.all()],
            "projects": [serialize_model_instance(p) for p in Project.query.all()],
            "project_images": [serialize_model_instance(pi) for pi in ProjectImage.query.all()],
            "videos": [serialize_model_instance(v) for v in Video.query.all()],
            "gallery": [serialize_model_instance(g) for g in GalleryItem.query.all()],
            "documents": [serialize_model_instance(d) for d in Document.query.all()],
            "skills": [serialize_model_instance(s) for s in Skill.query.all()],
            "experiences": [serialize_model_instance(e) for e in Experience.query.all()],
            "blog_posts": [serialize_model_instance(b) for b in BlogPost.query.all()],
            "activity_logs": [serialize_model_instance(a) for a in ActivityLog.query.order_by(ActivityLog.id.desc()).limit(100).all()],
        }
    }
    
    # Add record counts to metadata
    backup_data["metadata"]["record_counts"] = {
        tbl: len(rows) for tbl, rows in backup_data["tables"].items()
    }
    return backup_data

def export_database_to_json_str() -> str:
    """Returns the serialized backup as a formatted JSON string."""
    data = export_database_to_dict()
    return json.dumps(data, indent=2, default=str)

def restore_database_from_dict(backup_dict: dict) -> tuple[bool, str]:
    """
    Restores the database from a structured backup dictionary.
    Returns (success, message).
    """
    if not isinstance(backup_dict, dict) or "tables" not in backup_dict:
        return False, "Invalid backup format: missing 'tables' payload."

    tables = backup_dict["tables"]
    try:
        # 1. Site Settings
        if "site_settings" in tables and tables["site_settings"]:
            current_settings = SiteSetting.get_settings()
            for s_data in tables["site_settings"]:
                for key, val in s_data.items():
                    if key != "id" and hasattr(current_settings, key):
                        if "last_run" in key and val:
                            try:
                                val = datetime.fromisoformat(val)
                            except Exception:
                                val = None
                        setattr(current_settings, key, val)

        # 2. Projects
        if "projects" in tables:
            for p_data in tables["projects"]:
                existing = Project.query.filter_by(slug=p_data.get("slug")).first()
                if existing:
                    for k, v in p_data.items():
                        if k not in ("id", "created_at", "updated_at") and hasattr(existing, k):
                            setattr(existing, k, v)
                else:
                    clean_p = {k: v for k, v in p_data.items() if k not in ("id", "created_at", "updated_at")}
                    db.session.add(Project(**clean_p))

        # 3. Videos
        if "videos" in tables:
            for v_data in tables["videos"]:
                existing = Video.query.filter_by(slug=v_data.get("slug")).first()
                if existing:
                    for k, v in v_data.items():
                        if k not in ("id", "created_at") and hasattr(existing, k):
                            setattr(existing, k, v)
                else:
                    clean_v = {k: v for k, v in v_data.items() if k not in ("id", "created_at")}
                    db.session.add(Video(**clean_v))

        # 4. Skills
        if "skills" in tables:
            for s_data in tables["skills"]:
                existing = Skill.query.filter_by(name=s_data.get("name")).first()
                if existing:
                    for k, v in s_data.items():
                        if k not in ("id",) and hasattr(existing, k):
                            setattr(existing, k, v)
                else:
                    clean_s = {k: v for k, v in s_data.items() if k not in ("id",)}
                    db.session.add(Skill(**clean_s))

        # 5. Categories
        if "categories" in tables:
            for c_data in tables["categories"]:
                existing = Category.query.filter_by(slug=c_data.get("slug")).first()
                if not existing:
                    clean_c = {k: v for k, v in c_data.items() if k not in ("id",)}
                    db.session.add(Category(**clean_c))

        # 6. Experiences
        if "experiences" in tables:
            for e_data in tables["experiences"]:
                existing = Experience.query.filter_by(company=e_data.get("company"), role=e_data.get("role")).first()
                if not existing:
                    clean_e = {k: v for k, v in e_data.items() if k not in ("id",)}
                    db.session.add(Experience(**clean_e))

        db.session.commit()
        return True, "Database restoration completed successfully!"
    except Exception as e:
        db.session.rollback()
        return False, f"Restoration error: {str(e)}"

