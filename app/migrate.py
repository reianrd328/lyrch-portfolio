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
                    ("backup_last_status", "VARCHAR(150) DEFAULT 'Never run'"),
                    ("gdrive_backup_enabled", "BOOLEAN DEFAULT 0"),
                    ("gdrive_folder_id", "VARCHAR(120) DEFAULT ''"),
                    ("gdrive_last_upload_url", "VARCHAR(255) NULL")
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
        except Exception as e:
            app.logger.warning(f"Migration checker notice: {e}")

