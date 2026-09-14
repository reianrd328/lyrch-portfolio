import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from app.models import db, SiteSetting, ActivityLog
from app.services.backup_service import export_database_to_dict, export_database_to_json_str
from app.services.email_service import send_backup_email, is_smtp_configured

cron_bp = Blueprint("cron", __name__, url_prefix="/api/cron")

@cron_bp.route("/daily-backup", methods=["GET", "POST"])
def daily_backup_cron():
    """
    Automated daily backup webhook endpoint.
    Protected by CRON_SECRET or SECRET_KEY token.
    Pinging this endpoint triggers daily backup dispatch if backup_auto_enabled is True.
    """
    token = request.args.get("token") or request.headers.get("X-Cron-Token")
    expected_token = os.getenv("CRON_SECRET", current_app.config.get("SECRET_KEY", "lyrch-backup-secret"))

    if not token or token != expected_token:
        return jsonify({"success": False, "error": "Unauthorized: invalid or missing cron token."}), 403

    settings = SiteSetting.get_settings()
    if not settings.backup_auto_enabled:
        return jsonify({
            "success": True,
            "status": "skipped",
            "message": "Automated daily backup is currently toggled OFF in Admin settings."
        })

    if not settings.backup_email:
        settings.backup_last_status = "Failed: No recipient email configured in settings."
        db.session.commit()
        return jsonify({
            "success": False,
            "status": "error",
            "error": "No backup recipient email configured in settings."
        }), 400

    backup_dict = export_database_to_dict()
    backup_json_str = export_database_to_json_str()

    success, msg = send_backup_email(settings.backup_email, backup_json_str, backup_dict["metadata"])
    settings.backup_last_run = datetime.utcnow()
    settings.backup_last_status = ("Success: " if success else "Error: ") + msg

    log = ActivityLog(
        title=f"Automated Daily Backup {'dispatched' if success else 'failed'}",
        activity_type="project",
        time_label="Just now"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "success": success,
        "message": msg,
        "timestamp": settings.backup_last_run.isoformat()
    })

