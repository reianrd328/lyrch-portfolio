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

    # Support reverse proxy headers (e.g. Render HTTPS forwarding)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Ensure upload directories exist
    upload_root = app.config["UPLOAD_FOLDER"]
    for sub in ["projects", "videos", "gallery", "documents", "profile"]:
        os.makedirs(os.path.join(upload_root, sub), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Auto-initialize database tables and seed demo data on fresh deployment (e.g. Render)
    with app.app_context():
        try:
            db.create_all()
            if not app.config.get("TESTING") and User.query.count() == 0:
                from app.seed import seed_initial_data
                seed_initial_data()
            if not app.config.get("TESTING"):
                from app.migrate import check_and_apply_migrations
                check_and_apply_migrations(app)
        except Exception as e:
            app.logger.warning(f"Database auto-setup notice: {e}")

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
    from app.routes.cron import cron_bp
    from app.routes.profiles import profiles_bp

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
    app.register_blueprint(cron_bp)
    app.register_blueprint(profiles_bp, url_prefix="/admin/profiles")

    # Enforce Single Active Device Session on all Admin routes
    @app.before_request
    def enforce_single_admin_session():
        from flask import session, request, redirect, url_for, flash
        from flask_login import current_user, logout_user
        from datetime import datetime

        if not app.config.get("TESTING") and current_user.is_authenticated and request.path.startswith("/admin"):
            sess_token = session.get("admin_session_token")

            # If user has an active session token in DB and it doesn't match this browser's session
            if current_user.active_session_token and sess_token != current_user.active_session_token:
                session.pop("admin_session_token", None)
                logout_user()
                flash("Admin session closed: Your session was terminated or opened on another device.", "warning")
                return redirect(url_for("auth.login"))

            # Refresh heartbeat on user interaction
            if sess_token and current_user.active_session_token == sess_token:
                current_user.active_session_heartbeat = datetime.utcnow()
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

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

