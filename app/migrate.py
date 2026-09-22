from sqlalchemy import inspect, text
from app.models import db

def check_and_apply_migrations(app):
    """
    Ensures newly added columns (like backup fields) are added to existing databases
    without requiring manual SQL commands.
    """
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            if "site_settings" in inspector.get_table_names():
                existing_cols = {c["name"] for c in inspector.get_columns("site_settings")}
                new_cols = [
                    ("backup_auto_enabled", "BOOLEAN DEFAULT 0"),
                    ("backup_email", "VARCHAR(120) DEFAULT ''"),
                    ("backup_frequency", "VARCHAR(20) DEFAULT 'daily'"),
                    ("backup_last_run", "DATETIME NULL"),
                    ("backup_last_status", "TEXT NULL"),
                    ("gdrive_backup_enabled", "BOOLEAN DEFAULT 0"),
                    ("gdrive_folder_id", "VARCHAR(120) DEFAULT ''"),
                    ("gdrive_last_upload_url", "VARCHAR(255) NULL"),
                    ("gdrive_client_id", "VARCHAR(255) DEFAULT ''"),
                    ("gdrive_client_secret", "VARCHAR(255) DEFAULT ''"),
                    ("gdrive_refresh_token", "TEXT NULL"),
                    ("gdrive_user_email", "VARCHAR(120) NULL"),
                    ("resend_api_key", "VARCHAR(255) DEFAULT ''"),
                    ("resume_url", "VARCHAR(255) NULL"),
                    ("contact_title", "VARCHAR(150) DEFAULT 'Initiate Connection'"),
                    ("contact_status", "VARCHAR(100) DEFAULT 'Available for Select Contracts'"),
                    ("contact_description", "TEXT NULL")
                ]
                for col_name, col_def in new_cols:
                    if col_name not in existing_cols:
                        try:
                            db.session.execute(text(f"ALTER TABLE site_settings ADD COLUMN {col_name} {col_def}"))
                            db.session.commit()
                            app.logger.info(f"Added column {col_name} to site_settings.")
                        except Exception as err:
                            db.session.rollback()
                            app.logger.warning(f"Migration notice for {col_name}: {err}")

                try:
                    db.session.execute(text("UPDATE site_settings SET contact_title = 'Initiate Connection' WHERE contact_title IS NULL OR contact_title = ''"))
                    db.session.execute(text("UPDATE site_settings SET contact_status = 'Available for Select Contracts' WHERE contact_status IS NULL OR contact_status = ''"))
                    db.session.execute(text("UPDATE site_settings SET contact_description = 'Have an IT challenge to solve, need a custom business management software, or looking to collaborate on generative AI productions? Dispatch your transmission below.' WHERE contact_description IS NULL OR contact_description = ''"))
                    db.session.commit()
                except Exception as err:
                    db.session.rollback()

            if "users" in inspector.get_table_names():
                existing_user_cols = {c["name"] for c in inspector.get_columns("users")}
                new_user_cols = [
                    ("active_session_token", "VARCHAR(64) NULL"),
                    ("active_session_device", "VARCHAR(255) NULL"),
                    ("active_session_heartbeat", "DATETIME NULL"),
                    ("active_session_ip", "VARCHAR(64) NULL"),
                    ("profile_id", "INTEGER NULL")
                ]
                for col_name, col_def in new_user_cols:
                    if col_name not in existing_user_cols:
                        try:
                            db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                            db.session.commit()
                            app.logger.info(f"Added column {col_name} to users.")
                        except Exception as err:
                            db.session.rollback()
                            app.logger.warning(f"Migration notice for users.{col_name}: {err}")

            # Check and migrate videos table for album column
            if "videos" in inspector.get_table_names():
                video_cols = {c["name"] for c in inspector.get_columns("videos")}
                if "album" not in video_cols:
                    try:
                        db.session.execute(text("ALTER TABLE videos ADD COLUMN album VARCHAR(100) NULL"))
                        db.session.commit()
                        app.logger.info("Added column album to videos table.")
                    except Exception as err:
                        db.session.rollback()
                        app.logger.warning(f"Migration notice for videos.album: {err}")

            # Check and migrate gallery table for project_id, visibility, tags, file_size_bytes
            if "gallery" in inspector.get_table_names():
                gallery_cols = {c["name"] for c in inspector.get_columns("gallery")}
                new_gallery_cols = [
                    ("project_id", "INTEGER NULL"),
                    ("visibility", "VARCHAR(20) DEFAULT 'published'"),
                    ("tags", "VARCHAR(255) NULL"),
                    ("file_size_bytes", "INTEGER DEFAULT 0")
                ]
                for col_name, col_def in new_gallery_cols:
                    if col_name not in gallery_cols:
                        try:
                            db.session.execute(text(f"ALTER TABLE gallery ADD COLUMN {col_name} {col_def}"))
                            db.session.commit()
                            app.logger.info(f"Added column {col_name} to gallery table.")
                        except Exception as err:
                            db.session.rollback()
                            app.logger.warning(f"Migration notice for gallery.{col_name}: {err}")
        except Exception as e:
            app.logger.warning(f"Migration checker notice: {e}")

        # Check and initialize site_settings.gallery_categories
        try:
            inspector = inspect(db.engine)
            if "site_settings" in inspector.get_table_names():
                setting_cols = {c["name"] for c in inspector.get_columns("site_settings")}
                if "gallery_categories" not in setting_cols:
                    try:
                        # Add column without server DEFAULT to support MySQL / TiDB / SQLite / PostgreSQL
                        db.session.execute(text("ALTER TABLE site_settings ADD COLUMN gallery_categories TEXT NULL"))
                        db.session.commit()
                        app.logger.info("Added column gallery_categories to site_settings table.")
                    except Exception as err:
                        db.session.rollback()
                        app.logger.warning(f"Migration notice for site_settings.gallery_categories: {err}")

                # Populate default categories if NULL or empty
                try:
                    db.session.execute(text("UPDATE site_settings SET gallery_categories = 'UI / UX, Projects, AI, Branding, Screenshots, Graphics, Other' WHERE gallery_categories IS NULL OR gallery_categories = ''"))
                    db.session.commit()
                except Exception as err:
                    db.session.rollback()
        except Exception as e:
            app.logger.warning(f"Site settings migration notice: {e}")

        # Check and initialize portfolio_profiles table
        try:
            from app.models.profile import PortfolioProfile
            from app.services.profile_service import bootstrap_default_profile_if_needed

            PortfolioProfile.__table__.create(db.engine, checkfirst=True)

            # Ensure is_published column exists
            inspector = inspect(db.engine)
            if "portfolio_profiles" in inspector.get_table_names():
                prof_cols = {c["name"] for c in inspector.get_columns("portfolio_profiles")}
                if "is_published" not in prof_cols:
                    try:
                        db.session.execute(text("ALTER TABLE portfolio_profiles ADD COLUMN is_published BOOLEAN DEFAULT 1"))
                        db.session.commit()
                        app.logger.info("Added column is_published to portfolio_profiles.")
                    except Exception as err:
                        db.session.rollback()
                        app.logger.warning(f"Migration notice for is_published: {err}")

            bootstrap_default_profile_if_needed()
        except Exception as e:
            app.logger.warning(f"Portfolio profiles migration notice: {e}")

        # Check and populate default career experiences if table is empty
        try:
            from app.models.experience import Experience
            if Experience.query.count() == 0:
                default_experiences = [
                    {
                        "role_title": "Senior IT Support Specialist & Systems Administrator",
                        "company": "Nationwide Multi-Branch Support",
                        "location": "Philippines",
                        "period": "2018 — Present",
                        "description": "Orchestrating hardware, networking, and software systems across 100+ branches. Engineered custom helpdesk ticketing tools, automated triage scripts, and centralized remote desktop support infrastructure.",
                        "order_index": 1
                    },
                    {
                        "role_title": "IT Infrastructure & Technical Support Engineer",
                        "company": "Corporate IT Operations",
                        "location": "Philippines",
                        "period": "2012 — 2018",
                        "description": "Delivered Level 2/3 technical diagnostics, network routing, point-of-sale integrations, and database migrations. Reduced mean time to resolution (MTTR) by 45% through custom automated diagnostic routines.",
                        "order_index": 2
                    },
                    {
                        "role_title": "IT Systems Support Technician",
                        "company": "Hardware & Network Field Operations",
                        "location": "Philippines",
                        "period": "2008 — 2012",
                        "description": "Frontline diagnostics, workstation rollout, server maintenance, and remote user support. Established the foundational discipline of 24/7 problem solving and customer-first technical triage.",
                        "order_index": 3
                    }
                ]
                for exp_item in default_experiences:
                    db.session.add(Experience(**exp_item))
                db.session.commit()
                app.logger.info("Populated default career experiences.")
        except Exception as e:
            app.logger.warning(f"Experience bootstrap notice: {e}")

        # Check and ensure contact_messages table exists
        try:
            from app.models.message import ContactMessage
            ContactMessage.__table__.create(db.engine, checkfirst=True)
        except Exception as e:
            app.logger.warning(f"ContactMessage table migration notice: {e}")


