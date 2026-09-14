import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from app.models import db, SiteSetting, ActivityLog
from app.services.backup_service import export_database_to_dict, export_database_to_json_str
from app.services.email_service import send_backup_email, is_smtp_configured
from app.services.gdrive_service import upload_backup_to_gdrive, is_gdrive_configured

cron_bp = Blueprint("cron", __name__, url_prefix="/api/cron")

@cron_bp.route("/daily-backup", methods=["GET", "POST"])
def daily_backup_cron():
    """
    Automated daily backup webhook endpoint.
    Protected by CRON_SECRET or SECRET_KEY token.
    Pinging this endpoint triggers daily backup dispatch to Google Drive and/or Email.
    """
    token = request.args.get("token") or request.headers.get("X-Cron-Token")
    expected_token = os.getenv("CRON_SECRET", current_app.config.get("SECRET_KEY", "lyrch-backup-secret"))

    if not token or token != expected_token:
        return jsonify({"success": False, "error": "Unauthorized: invalid or missing cron token."}), 403

    settings = SiteSetting.get_settings()
    if not settings.backup_auto_enabled and not settings.gdrive_backup_enabled:
        return jsonify({
            "success": True,
            "status": "skipped",
            "message": "Automated backups (Email and Google Drive) are currently toggled OFF in Admin settings."
        })

    backup_dict = export_database_to_dict()
    backup_json_str = export_database_to_json_str()
    filename = f"lyrch_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    results = []
    has_error = False

    # 1. Google Drive Upload
    if settings.gdrive_backup_enabled:
        gd_success, gd_msg, gd_link = upload_backup_to_gdrive(
            backup_json_str,
            filename=filename,
            folder_id=settings.gdrive_folder_id
        )
        if gd_success:
            settings.gdrive_last_upload_url = gd_link
            results.append(f"Google Drive: Uploaded ({gd_msg})")
        else:
            has_error = True
            results.append(f"Google Drive Failed: {gd_msg}")

    # 2. Email Dispatch
    if settings.backup_auto_enabled and settings.backup_email:
        email_success, email_msg = send_backup_email(
            settings.backup_email,
            backup_json_str,
            backup_dict["metadata"]
        )
        if email_success:
            results.append(f"Email: Sent to {settings.backup_email}")
        else:
            has_error = True
            results.append(f"Email Failed: {email_msg}")
    elif settings.backup_auto_enabled and not settings.backup_email:
        has_error = True
        results.append("Email Failed: No recipient email configured in settings.")

    overall_msg = " | ".join(results) if results else "No backup destination configured."
    settings.backup_last_run = datetime.utcnow()
    settings.backup_last_status = (("Partial/Error: " if has_error else "Success: ") + overall_msg)[:500]

    log = ActivityLog(
        title=f"Cron Daily Backup {'completed' if not has_error else 'reported notice'}",
        activity_type="project",
        time_label="Just now"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "success": not has_error,
        "message": overall_msg,
        "details": results,
        "timestamp": settings.backup_last_run.isoformat()
    })
