import os
from flask import Flask, send_from_directory
from flask_login import LoginManager
from config import config_by_name
from app.models import db, User, SiteSetting

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Command clearance required. Please authenticate."
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Ensure upload directories exist
    upload_root = app.config["UPLOAD_FOLDER"]
    for sub in ["projects", "videos", "gallery", "documents"]:
        os.makedirs(os.path.join(upload_root, sub), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.public import public_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.projects import projects_bp
    from app.routes.videos import videos_bp
    from app.routes.gallery import gallery_bp
    from app.routes.documents import documents_bp
    from app.routes.skills import skills_bp
    from app.routes.experience import experience_bp
    from app.routes.blog import blog_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(projects_bp, url_prefix="/admin/projects")
    app.register_blueprint(videos_bp, url_prefix="/admin/videos")
    app.register_blueprint(gallery_bp, url_prefix="/admin/gallery")
    app.register_blueprint(documents_bp, url_prefix="/admin/documents")
    app.register_blueprint(skills_bp, url_prefix="/admin/skills")
    app.register_blueprint(experience_bp, url_prefix="/admin/experience")
    app.register_blueprint(blog_bp, url_prefix="/admin/blog")

    # Inject global site settings into all templates
    @app.context_processor
    def inject_settings():
        try:
            return {"settings": SiteSetting.get_settings()}
        except Exception:
            return {"settings": None}

    # Static uploads route
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return app

